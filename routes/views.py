from django.shortcuts import render, get_object_or_404, redirect
from reports.models import Report
from .models import Route, RouteReport, RouteTag, RouteTagging
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

# 失敗をログに残す
logger = logging.getLogger(__name__)

# ログイン済みかどうかチェック
def check_login(request):
    return 'user_id' in request.session


# 自分のルート一覧（ハンバーガーメニュ）
def myroute(request):
    if not check_login(request):
        return redirect('users:login')
    
    routes = Route.objects.filter(user_id=request.session.get('user_id'))
    return render(request, 'routes/myroute.html', {'routes': routes})


# ルート一覧画面（誰でも閲覧可能）
def route_list(request):
    routes = Route.objects.all()
    # タグ絞り込み：一覧画面のプルダウン（<select name="tag">）で選ばれたタグIDをGETパラメータで受け取る
    tag_id = request.GET.get('tag')
    if tag_id:
        # route_taggings(中間テーブル）経由でそのタグが付与されているルートだけに絞り込む
        # 同じルートに複数タグが付いていても中間テーブルの行が複数ヒットして重複しうるためdistinct()で除去
        routes = routes.filter(route_taggings__tag_id=tag_id).distinct()

    # プルダウンの選択肢として、有効な（論理削除されていない）タグを全件渡す
    tags = RouteTag.objects.all()
    return render(request, 'routes/route_list.html', {
        'routes': routes,
        'tags': tags,
        'selected_tag_id': tag_id,  # テンプレート側でプルダウンの選択状態を復元するために渡す
        })


# ルート詳細画面（誰でも閲覧可能）
def route_detail(request, pk):
    route = get_object_or_404(Route, pk=pk)
    return render(request, 'routes/route_detail.html', {'route': route})


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

    # ルートの地点を順番どおりに取得
    coords = [
        (float(rr.report.latitude), float(rr.report.longitude))
        for rr in route.route_reports.all()
    ]
    return JsonResponse(_compute_walk_route(coords))

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
    reports = Report.objects.all()

    # 地図JS(route_select.js)に渡すため、必要な項目だけJSON化する
    reports_data = [
        {
            "id": r.pk,
            "title": r.report_title,
            "description": r.report_description,
            "date": r.created_at.strftime("%Y年%m月%d日 %H:%M"),
            "lat": float(r.latitude),
            "lng": float(r.longitude),
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

    return render(request, 'routes/route_select_reports.html', {'reports': reports, 'reports_json': reports_json, 'map_lat': center[0], 'map_lng': center[1], })

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

    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            route = form.save(commit=False)
            route.user_id = request.session.get('user_id')
            route.save()

            # 選択されたレポートに順番を付けて中間テーブルに保存
            # for order, report_id in enumerate(report_ids, start=1):
            #     RouteReport.objects.create(route=route, report_id=report_id, sequence_order=order)

            # 並び替え後の順番（作成画面のフォームから送られた report_ids）を優先
            # 無ければ選択時の順番（セッション）を使う
            ordered_ids = request.POST.getlist('report_ids') or report_ids
            # 選択されたレポートに順番を付けて中間テーブルに保存
            for order, report_id in enumerate(ordered_ids, start=1):
                RouteReport.objects.create(route=route, report_id=report_id, sequence_order=order)

            # 選択されたタグ（RouteTagのリスト）ごとに中間テーブル（RouteTagging）を作成
            # ルートは作成直後で既存タグの紐づけがないので、重複チェック不要でそのままcreateでよい
            for tag in form.cleaned_data['tags']:
                RouteTagging.objects.create(route=route, tag=tag)
            
            # 作成終了後、セッションに一時保存していたデータは削除
            if 'selected_report_ids' in request.session:
                del request.session['selected_report_ids']
            return redirect('routes:route_detail', pk=route.pk)
    else:
        form = RouteForm()

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

    return render(request, 'routes/route_create.html', {'reports': reports, 'form': form})


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
    
    if request.method == 'POST':
        form = RouteForm(request.POST, instance=route)
        if form.is_valid():
            form.save()

            # 編集時は既にタグが紐づいている可能性があるため、
            # 単純にcreateするのではなく「選択解除されたタグを外し、新たに選ばれたタグだけ追加する」差分更新にする
            selected_tags = form.cleaned_data['tags']

            # 1. フォームで選ばれなかった（チェックが外れた）タグの紐づけを削除
            #    RouteTaggingは中間テーブルなので、ここでの delete() は物理削除
            route.route_taggings.exclude(tag__in=selected_tags).delete()

            # 2. まだ紐づいていない、新たに選ばれたタグだけを追加
            #    （既に紐づいているタグをcreateしようとするとunique_together制約でエラーになるため、
            #     既存タグIDのセットを作って差分だけ処理）
            existing_tag_ids = set(route.route_taggings.values_list('tag_id', flat=True))
            for tag in selected_tags:
                if tag.id not in existing_tag_ids:
                    RouteTagging.objects.create(route=route, tag=tag)
            return redirect('routes:route_detail', pk=route.pk)
        # 無効な入力の場合、下のrenderで再表示する
    else:
        # GET時：編集画面を開いた時点で、既に紐づいているタグをプルダウンの選択済み状態にする
        # ModelMultipleChoiceFieldのinitialにはpkのリストを渡せばよい
        form = RouteForm(instance=route,
                         initial={
                             'tags': route.route_taggings.values_list('tag_id', flat=True),
        })    # GET時、既存データが入ったフォームを用意

    return render(request, 'routes/route_edit.html', {'route': route, 'form': form})


# ルート削除処理（POST専用）
def route_delete(request, pk):
    if not check_login(request):
        return redirect('users:login')

    route = get_object_or_404(Route, pk=pk)

    # 作成者以外は削除できない
    if str(route.user_id) != str(request.session.get('user_id')):
        return redirect('routes:route_detail', pk=route.pk)
    
    route.delete()
    return redirect('routes:myroute')
