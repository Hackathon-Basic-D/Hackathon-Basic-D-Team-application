from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment
from django.conf import settings # 追記

def environment(**options):
    env = Environment(**options)

    def url(viewname, *args, **kwargs):
        return reverse(viewname, args=args or None, kwargs=kwargs or None)

    env.globals.update({
        'static': static,
        'url': url,
        # .envファイル⇒docker-compose.yml⇒config/settings.py⇒ここに値が渡る
        'GOOGLE_MAPS_API_KEY_FRONT': settings.GOOGLE_MAPS_API_KEY_FRONT,   # 追記
    })
    return env

# ログイン状態を全テンプレートに自動で渡すための関数
# settings.pyのcontext_processorに登録することで、Djangoがrender()の直前に
# 毎回この関数をrequest付きで呼び出し、戻り値のdictを自動でcontextに足してくれる
# 各view側でrender(..., {'logged_in': ...})と書かなくても、
# header.htmlの{% if logged_in %}がどのページでもそのまま動くようになる
def auth_status(request):
    # ログイン成功時にrequest.session['user_id']へIDを挿入
    # 「セッションにuser_idが入っているかどうか」でログイン中かどうかを判定
    return {'logged_in': 'user_id' in request.session}
