from django.shortcuts import render, get_object_or_404, redirect
from reports.models import Report
from .models import Route, RouteReport
from .forms import RouteForm
import json
import urllib.request
import urllib.error
from django.conf import settings
from django.http import JsonResponse
import logging

from users.models import User
from users.areas import get_area_center, DEFAULT_CENTER
from django.core.exceptions import ValidationError

from django.db.models import Q   # 複数条件を OR/AND/NOT で組み立てる Django のクエリオブジェクト

# タイトル先頭の【…】抽出・付与（地域ラベル用）
#   extract_region(title)            : タイトル先頭の【…】の中身（例 '大阪府'）。無ければ ''
#   with_region_prefix(title, region): 先頭の既存【…】を外して【region】を付け直す（region空なら【その他】）
#   UNKNOWN_REGION                   : 判定不可のときの代替ラベル
from users.regions import extract_region, with_region_prefix, UNKNOWN_REGION

import time   # 経路線の回数制限で、前回計算した時刻を記録するため
# 同じルートの経路線を続けて計算できる回数の上限
# Routes API は呼ぶたびに課金さるため、同じルートのリロードが繰り返されたときに際限なく計算しないようにする
MAX_POLYLINE_CALLS_PER_ROUTE = 5

# 上のカウントをリセットするまでの間隔（秒）。
# 前回の計算からこの時間が空いていれば、同じルートでもカウントを0に戻す。
# 「短時間に繰り返し開いたとき」だけを止めたいので、時間が経てば自然に回復させる。
POLYLINE_COUNT_RESET_SECONDS = 30 * 60   # 30分

# 失敗をログに残す
logger = logging.getLogger(__name__)

# 経路に含めるレポート数の制限（route_select.js の MIN_SPOTS/MAX_SPOTS と一致させる）
MIN_REPORTS_PER_ROUTE = 2   # 最小2件（経路線に必要）
MAX_REPORTS_PER_ROUTE = 3   # 最大3件（GoogleマップURLのモバイル経由地上限）

# ログイン済みかどうかチェック
def check_login(request):
    return 'user_id' in request.session


# 自分のルート一覧（ハンバーガーメニュ）
def myroute(request):
    if not check_login(request):
        return redirect('users:login')
    
    routes = Route.objects.filter(user_id=request.session.get('user_id'))
    q = request.GET.get('q', '').strip()   # 検索キーワード（GETの ?q=）
    if q:
        routes = routes.filter(Q(route_title__icontains=q) | Q(route_description__icontains=q))
    return render(request, 'routes/myroute.html', {'routes': routes, 'q': q})


# ルート一覧画面（誰でも閲覧可能）
def route_list(request):
    q = request.GET.get('q', '').strip()   # 検索キーワード（GETの ?q=）
    routes = Route.objects.all()
    if q:
        # 「タイトル または 本文」に部分一致（OR）。通常の filter(kwargs) は AND になるため Q で OR を表現。
        # __icontains は大文字小文字を無視した部分一致（SQL の LIKE '%q%'）。
        routes = routes.filter(Q(route_title__icontains=q) | Q(route_description__icontains=q))
    return render(request, 'routes/route_list.html', {'routes': routes, 'q': q})


# ルート詳細画面（誰でも閲覧可能）
def route_detail(request, pk):
    route = get_object_or_404(Route, pk=pk)
    session_uid = request.session.get('user_id')
    # 所有者判定：session(文字列) と route.user_id を文字列同士で比較（report_detail と同じ方式）
    is_owner = session_uid is not None and route.user_id is not None and str(route.user_id) == str(session_uid)
    return render(request, 'routes/route_detail.html', {'route': route, 'is_owner': is_owner})


# 座標リスト [(lat, lng), ...] から徒歩ルートを Routes API で計算して dict を返す（詳細画面・プレビュー共通）
def _compute_walk_route(coords):
    if len(coords) < 2:
        return {"polyline": ""}   # 2地点未満は線なし

    origin, destination = coords[0], coords[-1]
    intermediates = coords[1:-1]

    body = {
        "origin":      {"location": {"latLng": {"latitude": origin[0],      "longitude": origin[1]}}},
        "destination": {"location": {"latLng": {"latitude": destination[0], "longitude": destination[1]}}},
        "intermediates": [
            {"location": {"latLng": {"latitude": lat, "longitude": lng}}}
            for lat, lng in intermediates
        ],
        "travelMode": "WALK",
        "optimizeWaypointOrder": False,
        "polylineEncoding": "ENCODED_POLYLINE",
    }

    req = urllib.request.Request(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY_BACK,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.warnings,routes.polyline.encodedPolyline",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'ignore')
        logger.error("Routes API HTTPError %s: %s", e.code, detail)
        return {"polyline": "", "error": f"HTTP {e.code}: {detail}"}
    except Exception as e:
        logger.error("Routes API error: %s", e)
        return {"polyline": "", "error": str(e)}

    routes = data.get("routes", [])
    route0 = routes[0] if routes else {}
    encoded = route0.get("polyline", {}).get("encodedPolyline", "")
    dur_str = route0.get("duration", "")
    duration_sec = int(float(dur_str[:-1])) if dur_str.endswith("s") else None
    return {
        "polyline": encoded,
        "duration_seconds": duration_sec,
        "distance_meters": route0.get("distanceMeters"),
        "warnings": route0.get("warnings", []),
    }

# ルートの徒歩経路線(ポリライン)を Routes API で計算して JSON で返す
# ・バックエンドのキー(GOOGLE_MAPS_API_KEY_BACK)を使う（ブラウザに晒さない）
# ・規約に沿って保存はせず、呼ばれるたびに計算する
def route_polyline(request, pk):
    route = get_object_or_404(Route, pk=pk)

    # 経路計算は Routes API を呼ぶ＝呼ぶたびに課金されるため、ログイン中だけに限定
    # ルート詳細の地図・マーカー・順番は未ログインでも表示される
    # 未ログインで出なくなるのは経路線と距離・所要時間だけ
    if not check_login(request):
        return JsonResponse({'polyline': '', 'reason': 'login_required'}, status=403)

    # 同じルートを続けて計算した回数をセッションで数える。次のどちらかでカウントを0に戻す
    #   ・直前に計算したルートと違う（別のルートを開いた）
    #   ・前回の計算から POLYLINE_COUNT_RESET_SECONDS 以上空いている
    # セッションはブラウザ単位なので、クッキーを消せばリセットされる
    # 意図的な連打を止めるものではなく、リロードの繰り返しで課金が積み上がるのを防ぐためのもの
    now = time.time()   # 現在時刻を秒数で取得
    last_pk = request.session.get('polyline_last_pk')
    last_at = request.session.get('polyline_last_at', 0)
    count = request.session.get('polyline_count', 0)
    if str(last_pk) != str(pk) or (now - last_at) > POLYLINE_COUNT_RESET_SECONDS:
        count = 0

    if count >= MAX_POLYLINE_CALLS_PER_ROUTE:
        # 429 = Too Many Requests → API は呼ばずに返す
        # 「最後に計算できた時刻」から数える
        return JsonResponse({'polyline': '', 'reason': 'too_many_requests'}, status=429)

    # ルートの地点を順番どおりに取得
    coords = [
        (float(rr.report.latitude), float(rr.report.longitude))
        for rr in route.route_reports.all()
    ]
    result = _compute_walk_route(coords)

    # 計算に失敗した回は数えない
    if not result.get('error'):
        request.session['polyline_last_pk'] = str(pk)
        request.session['polyline_last_at'] = now
        request.session['polyline_count'] = count + 1

    return JsonResponse(result)

# ルート作成のためのレポート選択画面
def route_select_reports(request):
    if not check_login(request):
        return redirect('users:login')

    if request.method == 'POST':
        # 選択されたレポートIDのリストをセッションに一時保存、作成画面へ引き継ぐ
        request.session['selected_report_ids'] = request.POST.getlist('report_ids')
        return redirect('routes:route_create')

    # 全てのレポートから選択
    # return render(request, 'routes/route_edit.html', {'reports': reports})
    # reports = Report.objects.all()
    reports = Report.objects.select_related('user').all()   # 作成者名も渡す（user を一緒に取得）

    # 地図JS(route_select.js)に渡すため、必要な項目だけJSON化する
    reports_data = [
        {
            "id": r.pk,
            "title": r.report_title,
            "description": r.report_description,
            "date": r.created_at.strftime("%Y年%m月%d日 %H:%M"),
            "lat": float(r.latitude),
            "lng": float(r.longitude),
            "user": r.user.user_name if r.user else "退会ユーザー",   # 作成者名（退会でNoneなら代替）
        }
        for r in reports
    ]
    # </script> でHTMLが壊れるのを防ぐため < をエスケープ
    reports_json = json.dumps(reports_data, ensure_ascii=False).replace("<", "\\u003c")

    # 地図の初期位置：ログイン中ユーザーのメインエリア（未ログインは来ないが念のため大阪）
    center = DEFAULT_CENTER
    try:
        user = User.objects.get(id=request.session.get('user_id'))
        center = get_area_center(user.main_area)
    except (User.DoesNotExist, ValidationError):
        pass
    
    # 編集モードのときだけ、現在のレポートを地図に初期選択させる（新規作成は空）
        # 新規作成の開始（route_list の作成ボタン ?new=1）は編集モード・選択をリセット
    if request.GET.get('new'):
        request.session.pop('edit_route_id', None)
        request.session.pop('selected_report_ids', None)
    # 現在の選択（編集＝現在のレポート／作成＝途中の選択）を地図に初期反映
    preselected = request.session.get('selected_report_ids', [])
    preselected_json = json.dumps([str(x) for x in preselected])
    
    return render(request, 'routes/route_select_reports.html', {'reports': reports, 'reports_json': reports_json, 'map_lat': center[0], 'map_lng': center[1], 'preselected_json': preselected_json, })

# 作成画面プレビュー用：保存前に report_ids（並び替え後の順番）から徒歩ルートを計算して返す
def route_preview(request):
    if not check_login(request):
        return JsonResponse({"polyline": "", "error": "not logged in"}, status=403)

    report_ids = request.POST.getlist('report_ids')
    # 送られてきた順（＝画面で並び替えた順）どおりに座標を組み立てる。
    # ここは順番が経路計算に直接効くため、filter の結果を report_ids の順に並べ直す
    reports = {str(r.pk): r for r in Report.objects.filter(pk__in=report_ids)}
    coords = [
        (float(reports[str(rid)].latitude), float(reports[str(rid)].longitude))
        for rid in report_ids if str(rid) in reports
    ]
    return JsonResponse(_compute_walk_route(coords))

# ルート作成画面
def route_create(request):
    if not check_login(request):
        return redirect('users:login')

    # select_reportsで選んだレポートIDをセッションから取り出す
    report_ids = request.session.get('selected_report_ids', [])

    # 編集モード判定（route_edit がセットする edit_route_id）。他人のルートは編集させない
    edit_route = None
    edit_route_id = request.session.get('edit_route_id')
    if edit_route_id:
        edit_route = Route.objects.filter(pk=edit_route_id).first()
        if edit_route and str(edit_route.user_id) != str(request.session.get('user_id')):
            edit_route = None

    if request.method == 'POST':
        form = RouteForm(request.POST, instance=edit_route)  # 編集なら既存を更新、新規なら None（新規作成）
        if form.is_valid():
            # 並び替え後の順番（フォームの report_ids）を優先。無ければ選択時の順番（セッション）
            ordered_ids = request.POST.getlist('report_ids') or report_ids
            # --- サーバー側検証（クライアントJSを迂回した不正POST対策） ---
            # 重複除去（順番は維持）
            seen = set()
            ordered_ids = [rid for rid in ordered_ids if not (rid in seen or seen.add(rid))]
            # 実在するReportのidだけに絞る（順番維持）
            existing = set(
                str(pk) for pk in Report.objects.filter(pk__in=ordered_ids).values_list('pk', flat=True)
            )
            ordered_ids = [rid for rid in ordered_ids if str(rid) in existing]
            # 件数チェック（route_select.js の MIN/MAX と一致）
            if not (MIN_REPORTS_PER_ROUTE <= len(ordered_ids) <= MAX_REPORTS_PER_ROUTE):
                form.add_error(None, f'ルートには有効なレポートを{MIN_REPORTS_PER_ROUTE}〜{MAX_REPORTS_PER_ROUTE}件選んでください。')
            else:
                route = form.save(commit=False)
                if edit_route is None:   # 新規のみ作成者をセット（編集は元の作成者を維持）
                    route.user_id = request.session.get('user_id')
                # ルートタイトル先頭に地域ラベルを付ける
                # 含まれるレポートのタイトル先頭の【…】を集約して作る（座標から再判定しない）
                # ordered_ids（検証済みの並び順）の順に地域を抽出→重複除去→'・'で連結
                _reports_by_id = {str(r.pk): r for r in Report.objects.filter(pk__in=ordered_ids)}
                _regions = []
                for _rid in ordered_ids:
                    _r = _reports_by_id.get(str(_rid))
                    if _r is None:
                        continue
                    _reg = extract_region(_r.report_title)   # 例 '大阪府'（'その他' の場合もある）
                    if _reg and _reg not in _regions:        # 重複除去（順番は維持）
                        _regions.append(_reg)
                # 1件も取れなければ with_region_prefix 側で【その他】が付く
                route.route_title = with_region_prefix(route.route_title, '・'.join(_regions))
                route.save()

                # 編集は含めるレポートの追加・削除もあり＝行数と構成が変わるため、
                # 差分UPDATEではなく古い中間テーブル行を消して作り直す。新規は行が無いので削除不要。
                if edit_route is not None:
                    route.route_reports.all().delete()
                # 上で検証済みの ordered_ids の順で作成（生fetchで上書きしない＝#3検証を保存に反映）
                for order, report_id in enumerate(ordered_ids, start=1):
                    RouteReport.objects.create(route=route, report_id=report_id, sequence_order=order)
                
                # 作成終了後、セッションに一時保存していたデータは削除
                request.session.pop('selected_report_ids', None)
                request.session.pop('edit_route_id', None)
                return redirect('routes:route_detail', pk=route.pk)
    else:
        # GET：編集なら既存のタイトル・本文を初期表示
        form = RouteForm(instance=edit_route)

    # 選択済みのレポートをDBから取得
    reports = Report.objects.filter(pk__in=report_ids)
    # IDからReportを取り出せるようにする
    reports_dict = {str(report.pk): report for report in reports}
    # セッションのID順にReportを並べ直す
    reports = [
        reports_dict[str(report_id)]
        for report_id in report_ids
        if str(report_id) in reports_dict
    ]

    # 作成画面に「先頭に【○○】が付きます」と見せるための地域ラベル（表示用）
    # 保存時と同じ集約ロジックで作り、表示と保存結果を一致
    _regions = []
    for _r in reports:
        _reg = extract_region(_r.report_title)
        if _reg and _reg not in _regions:
            _regions.append(_reg)
    region = '・'.join(_regions) or UNKNOWN_REGION   # 空なら【その他】

    return render(request, 'routes/route_create.html', {'reports': reports, 'form': form, 'is_edit': edit_route is not None, 'region': region})


# ルート編集画面
# GET:既存データが入ったフォームを用意
# POST:更新処理
def route_edit(request, pk):
    if not check_login(request):
        return redirect('users:login')

    route = get_object_or_404(Route, pk=pk)

    # 作成者以外は編集できない
    if str(route.user_id) != str(request.session.get('user_id')):
        return redirect('routes:route_detail', pk=route.pk)

    # 編集は作成フローに相乗り（編集モード）。対象ルートpkと現在のレポートid（順番どおり）を
    # セッションに入れて、地図での選び直し（route_select）からやり直す。保存は route_create 側で更新。
    request.session['edit_route_id'] = str(route.pk)
    request.session['selected_report_ids'] = [
        str(rr.report_id)
        for rr in route.route_reports.all().order_by('sequence_order')
    ]
    # 編集は地図を通さず作成画面へ直行（現在のレポートは reorder に出る）。地図は「選び直す」でだけ開く
    return redirect('routes:route_create')


# ルート削除処理（POST専用）
def route_delete(request, pk):
    if not check_login(request):
        return redirect('users:login')

    route = get_object_or_404(Route, pk=pk)

    # 作成者以外は削除できない
    if str(route.user_id) != str(request.session.get('user_id')):
        return redirect('routes:route_detail', pk=route.pk)

    # 誤削除防止：削除は POST のときだけ実行する（reports/views.py の report_delete と同じ方針）
    # GET でも削除できる状態だと、/routes/<pk>/delete/ を直接開くだけで消えてしまう
    if request.method != 'POST':
        return redirect('routes:route_detail', pk=route.pk)
    
    route.delete()
    return redirect('routes:myroute')
