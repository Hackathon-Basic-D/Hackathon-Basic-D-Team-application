from django.shortcuts import render, get_object_or_404, redirect
from .models import Report, ReportComment
from .forms import ReportForm

# default_storage: Djangoが提供するファイル保存の抽象化API
# 今はFileSystemStorage（ローカル保存）を使用
# 後でsettings.pyのSTORAGES設定をS3Boto3Storageに変えるだけで
# ここのコードは変更せずにS3保存に切り替え可能
from django.core.files.storage import default_storage
from django.urls import reverse   # 成功メッセージ用に ?created=1 を付けてリダイレクトするため
from django.db.models import Q   # 複数条件を OR/AND/NOT で組み立てる Django のクエリオブジェクト

# 緯度経度から地域（都道府県）を判定し、タイトル先頭に地域ラベルを付ける
#   prefecture_of(lat, lng) : 座標 → 都道府県名（例 '大阪府'）。該当なし（海上・国外・不正値）は ''
from users.regions import prefecture_of, UNKNOWN_REGION

# ログイン済みかどうかチェック
def check_login(request):
    return 'user_id' in request.session


# 自分のレポート一覧（ハンバーガーメニュー)
def mypost(request):
    if not check_login(request):
        return redirect('users:login')  # 未ログインの場合、ログイン画面へ遷移

    # ログイン中のuser_idに紐づくレポートのみ取り込む    
    reports = Report.objects.filter(user_id=request.session.get('user_id'))
    q = request.GET.get('q', '').strip()   # 検索キーワード（GETの ?q=）
    if q:
        reports = reports.filter(Q(report_title__icontains=q) | Q(report_description__icontains=q))
    return render(request, 'reports/mypost.html', {'reports': reports, 'q': q})

# レポート一覧（公開・未ログインでも表示・キーワード検索）
def report_list(request):
    q = request.GET.get('q', '').strip()   # 検索キーワード（GETの ?q=）
    reports = Report.objects.all()          # SoftDeleteManager が削除済みを自動除外
    if q:
        # 「タイトル または 本文」に部分一致（OR）。__icontains は大小無視の部分一致（LIKE '%q%'）
        reports = reports.filter(Q(report_title__icontains=q) | Q(report_description__icontains=q))
    return render(request, 'reports/report_list.html', {'reports': reports, 'q': q})

# 緯度・経度を小数8桁に丸めるヘルパー。
# 目的：Googleマップ由来の座標は小数十数桁あり、DBの桁数上限（緯度10桁/経度11桁）を超えて弾かれる
#       クライアントの値をそのまま信用せず、サーバ側で桁を落として正規化
def _round_coord(v):
    try:
        return f"{float(v):.8f}"   # 例: 34.68630012 → "34.68630012"（8桁固定）
    except (TypeError, ValueError):
        return v                     # 数値化できない値（None・空・不正文字列）はそのまま返し、後段の検証に任せる


# レポート作成画面
# GET:フォーム表示
# POST:保存処理
def report_create(request):
    if not check_login(request):
            return redirect('users:login')
    if request.method == 'POST':
        # 送信された緯度・経度を、フォーム検証の前に桁丸めする（クライアント由来の値を信用せずサーバで正規化）
        data = request.POST.copy()                      # request.POST は変更不可なのでコピーを作る
        for key in ('latitude', 'longitude'):           # 緯度・経度の2項目について
            if data.get(key):                           # 値が入っているときだけ処理（空なら必須エラーに任せる）
                data[key] = str(_round_coord(data[key]))  # 8桁に丸め、文字列として入れ直す
        # request.FILESを渡さないとアップロードされた画像を受け取れない
        form = ReportForm(data, request.FILES)          # 丸めた data でフォームを作る（request.POST の代わり）

        if form.is_valid():
            # commit=Falseで一旦DB保存せず、投稿者(user_id)をセットしてから保存する
            report = form.save(commit=False)
            report.user_id = request.session.get('user_id')

            # Reportモデルには画像URL文字列のカラム（report_image_url）しかないため、
            # ここで変換する必要がある
            uploaded_image = form.cleaned_data.get('report_image') # 写真そのものを取り出す
            if uploaded_image:
                # 保存先パスに"reports/"プレフィックスを付け、他用途のファイルと混ざらないようにする
                # save()は同名ファイルが既にあれば自動でユニークな名前にリネームしてくれる
                # 写真を実際に保存する
                saved_path = default_storage.save(f'reports/{uploaded_image.name}', uploaded_image)
                # 保存先パスからブラウザがアクセスできるURLを取得し、DBに保存するURLとして使う
                report.report_image_url = default_storage.url(saved_path)
                report.report_image_url = default_storage.url(saved_path)

            report.save()
            # return redirect('reports:report_detail', pk=report.pk)
            return redirect(f"{reverse('reports:report_detail', kwargs={'pk': report.pk})}?created=1")
    # form.is_valid()がFalseの場合、何もせずに下のrenderに進む
    else:
        initial = {
            # URLの lat/lng も丸めてから初期値にする（hidden に正規化済みの値が入る）
            'latitude': _round_coord(request.GET.get('lat')),
            'longitude': _round_coord(request.GET.get('lng')),
        }
        # GETならURLのlat/lngを初期値にしてフォームを表示
        form = ReportForm(initial=initial)

    # 作成画面に「タイトル先頭に【○○】が付きます」と“事前に”見せるための地域名を求める
    # サーバ側で判定する理由：判定に使う GeoJSON（約13MB）はブラウザに持たせたくないため、
    #                        画面描画のタイミングでサーバ側で計算して渡す
    # form['latitude'].value() の意味：
    #   ・GET（新規表示）    → 上の initial に入れた座標
    #   ・POST で入力不備の再表示 → 送信されてきた座標
    #   のどちらでも「今フォームに入っている座標」を返すので、その座標で都道府県を判定する
    region = prefecture_of(form['latitude'].value(), form['longitude'].value()) or UNKNOWN_REGION
    return render(request, 'reports/report_form.html', {'form': form, 'region': region})

# レポート詳細画面（未ログインでも閲覧可能）
def report_detail(request, pk):
    report = get_object_or_404(Report, pk=pk)   # 存在しないpkなら404エラー
    session_uid = request.session.get('user_id')
    # テンプレート側でループ処理できるように、紐づくコメントも一緒に返す
    comments = ReportComment.objects.filter(report=report)
    for c in comments:
        c.is_owner = session_uid is not None and str(c.user_id) == str(session_uid)
    # 所有者判定：session(文字列) と report.user_id(UUID) を文字列同士で比較（旧 == は型不一致で常にFalse）
    is_owner = session_uid is not None and report.user_id is not None and str(report.user_id) == str(session_uid)
    created = request.GET.get('created') == '1'   # 作成直後だけ成功メッセージ
    return render(request, 'reports/report_detail.html', {
        'report': report,
        'comments': comments,
        'user_id': request.session.get('user_id'),
        'is_owner': is_owner,
        'created': created,
    })


# レポート編集画面
# GET:フォーム表示
# POST:更新処理
def report_edit(request, pk):
    if not check_login(request):
        return redirect('users:login')

    report = get_object_or_404(Report, pk=pk)

    # レポート作成者以外は編集できない（詳細画面へ遷移）
    if str(report.user_id) != str(request.session.get('user_id')):
        return redirect('reports:report_detail', pk=report.pk)
    
    if request.method == 'POST':
        # instance=reportを渡すことで「既存レコードの更新」として扱う
        form = ReportForm(request.POST, request.FILES, instance=report)
        if form.is_valid():
            report = form.save(commit=False)

            # 新しい画像が選択された場合のみ保存・URLを更新する
            uploaded_image = form.cleaned_data.get('report_image')
            if uploaded_image:
                saved_path = default_storage.save(f'reports/{uploaded_image.name}', uploaded_image)
                report.report_image_url = default_storage.url(saved_path)

            report.save()
            return redirect('reports:report_detail', pk=report.pk)
    else:
        form = ReportForm(instance=report)  # 既存の値が入ったフォームを表示

    # 編集画面でも「先頭に【○○】が付きます」を表示するため、既存レポートの座標から地域名を求める
    # （instance の緯度経度が form['latitude'].value() で取れる）
    region = prefecture_of(form['latitude'].value(), form['longitude'].value()) or UNKNOWN_REGION
    return render(request, 'reports/report_form.html', {'report': report, 'form': form, 'region': region})


# レポート削除処理(画面は持たない）
def report_delete(request, pk):
    if not check_login(request):
        return redirect('users:login')
    
    report = get_object_or_404(Report, pk=pk)
    # 投稿者以外は削除できない
    if str(report.user_id) != str(request.session.get('user_id')):
        return redirect('reports:report_detail', pk=report.pk)
    
    # 誤削除防止：削除は POST のときだけ
    if request.method == 'POST':
        report.delete() # models.pyで論理削除にオーバーライド
        return redirect('reports:mypost')
    return redirect('reports:report_detail', pk=report.pk)



# コメント作成処理(POST専用、レポート詳細画面のモーダル）
def comment_create(request, pk):
    if not check_login(request):
        return redirect('users:login')
    
    report = get_object_or_404(Report, pk=pk)
    comment_text = request.POST.get('report_comment')

    # 空文字・空白のコメントは保存しない
    if comment_text and comment_text.strip():
        ReportComment.objects.create(
            report=report,
            user_id=request.session.get('user_id'),
            report_comment=comment_text,
        )

    # 投稿してもしなくても、レポート詳細画面へ遷移
    return redirect('reports:report_detail', pk=report.pk)


# コメント削除処理(POST専用)
def comment_delete(request, pk):
    if not check_login(request):
        return redirect('users:login')
    
    comment = get_object_or_404(ReportComment, pk=pk)
    report_pk = comment.report_id   # コメント削除後、どのレポート詳細へ戻るか記憶しておく

    # コメント作成者以外は削除できない
    if str(comment.user_id) != str(request.session.get('user_id')):
        return redirect('reports:report_detail', pk=report_pk)
    
    comment.delete()
    return redirect('reports:report_detail', pk=report_pk)

# コメント編集処理（POST専用）
def comment_edit(request, pk):
    if not check_login(request):
        return redirect('users:login')

    comment = get_object_or_404(ReportComment, pk=pk)
    report_pk = comment.report_id

    # 作成者以外は編集できない
    if str(comment.user_id) != str(request.session.get('user_id')):
        return redirect('reports:report_detail', pk=report_pk)

    if request.method == 'POST':
        text = request.POST.get('report_comment', '')
        if text.strip():
            comment.report_comment = text
            comment.save(update_fields=['report_comment'])
    return redirect('reports:report_detail', pk=report_pk)
