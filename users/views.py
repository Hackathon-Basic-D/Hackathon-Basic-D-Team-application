from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
# next に渡されたURLが安全なURLかどうかを確認するための関数
# （外部サイトへ誘導される「オープンリダイレクト」対策として使用）
from django.utils.http import url_has_allowed_host_and_scheme

from .models import User
from .forms import SignUpForm, LoginForm, UserEditForm

import json                         # Reportのリストをjsonに変換
from reports.models import Report   # レポート一覧を取得するためインポート


# アプリを開いて最初に表示されるページ
# ログイン or 新規登録をクリックしてログイン画面・新規登録画面へ遷移
def welcome(request):
    return render(request, 'welcome.html')


# 新規登録画面
# GET:新規登録画面を表示
# POST:登録成功　→　ホーム画面へ遷移
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()  # SignUpForm.save()内で set_password()込みで保存される
            request.session['user_id'] = str(user.id)
            return redirect('users:home')   # ここでホーム画面へ遷移
    else:
        form = SignUpForm()

    return render(request, 'users/signup.html', {'form': form}) # GETなら登録フォームを表示

# ログイン画面
# GET:ログイン画面を表示
# POST:認証成功　→　ホーム画面へ遷移 / 認証失敗　→　ログイン画面を再表示
def login_view(request):
    # ログイン画面に「次にどこへ行くべきか」を next という名前で持ち回す。
    # 受け取り方は経由してきたルートによって変わる：
    # ・report_create等からリダイレクトした直後（GET） → クエリパラメータに入っている
    # ・ログインフォームを送信した直後（POST) → hidden input 'next' として送られてくる
    # 両方 or で拾うことで、GET・POSTどちらの経路でも next を取りこぼさない
    next_url = request.POST.get('next') or request.GET.get('next')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                request.session['user_id'] = str(user.id)


                # next をそのまま signal 通りに redirect() へ渡すのは危険。
                # 悪意あるユーザーが next=https://evil.example.com/ のような
                # 外部URLを仕込んでログインさせ、認証後にそこへ誘導する
                # 「オープンリダイレクト」攻撃を許してしまう。
                # url_has_allowed_host_and_scheme() で「このサイト自身のURLか」を
                # 確認できた場合のみ next へ飛ばし、それ以外は無視してホームへ通す。
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)   # 元々行おうとしていた操作に戻る
                # next がない（通常ログイン）の場合は、ホーム画面へ
                return redirect('users:home')   # ここでホーム画面へ遷移
            form.add_error(None, 'メールアドレスまたはパスワードが正しくありません')
    else:
        form = LoginForm()  # 認証失敗なら、ログイン画面を再表示

    # ここでの next_url は「まだ安全確認前の生の値」。
    # GET時（初回表示）・認証失敗時（フォーム再表示）のどちらでも next をテンプレートへ渡し、
    # login.html 側で hidden input として埋め込むことで、
    # 再送信（次のPOST）でも next を失わずに引き継げるようにする。
    return render(request, 'users/login.html', {'form': form, 'next':next_url})


# ログアウト
# セッションを破棄　→　ログイン画面へ遷移
def logout_view(request):
    request.session.flush()
    return redirect('users:login')  # ログアウト後は、ログイン画面へ遷移


# ホーム画面
# 未ログインでも表示可能
def home(request):
    # 論理削除されていないレポートを全件取得
    # Report.objects は SoftDeletemanager なので、deleted_at が入っていものは自動で除外
    reports = Report.objects.all()

    # 地図用JSに渡すため、必要な項目のみを辞書リストに整形してからJSON文字列化
    reports_json = json.dumps([
        {
            "id": r.pk,                                 # /reports/<id>/へ遷移するための主キー
            "title": r.report_title,                    # レポートのタイトル
            "description": r.report_description,        # 本文
            "lat": float(r.latitude),                   # JSONに変換するため、DecimalFieldをfloatに変換
            "lng": float(r.longitude),                  # 上記に同じ
            "date": r.created_at.strftime("%Y年%m月%d日 %H:%M"),    # 投稿日時
        }
        for r in reports
    ])
    # report_title / report_description はユーザー入力のため、"</script>"などで
    # scriptタグを閉じられないよう "</" をエスケープしてからテンプレートへ渡す
    # スクリプトインジェクション対策
    reports_json = reports_json.replace('</', '<\\/')

    # テンプレートに reports_jsonを渡す。home.html側で、window.REPORTS_DATAに埋め込み
    return render(request, 'users/home.html', {'reports_json': reports_json})

# 設定画面
# 未ログイン　→　ログイン画面へ遷移
# セッションはあるがDB上にユーザーが存在しない（削除済みなど）　→　404エラー画面へ遷移
# GET:設定画面を表示
# POST:更新成功　→　設定画面へ再遷移 / エラーあり　→　設定画面を再表示
def setting(request):
    if 'user_id' not in request.session:
        return redirect('users:login')  # 未ログインの場合、ログイン画面へ移動
    
    try:
        user = User.objects.get(id=request.session['user_id'])
    except (User.DoesNotExist, ValidationError):
        # DB上にユーザーが存在しない場合、
        # またはセッションのuser_idがUUIDとして不正な形式の場合、エラー画面へ
        return redirect('users:error404')
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('users:setting')
    else:
        form = UserEditForm(instance=user)

    return render(request, 'users/settings.html', {'form': form})
    
        
# 400エラー画面表示（不正なリクエスト時）
def error400(request, *args, **kwargs):
    return render(request, 'users/error400.html', status=400)

# 404エラー画面表示（ページ・リソースが見つからない時）
def error404(request, *args, **kwargs):
    return render(request, 'users/error404.html', status=404)

# 500エラー画面表示（サーバー内部エラー時）
def error500(request, *args, **kwargs):
    return render(request, 'users/error500.html', status=500)
