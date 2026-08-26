from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment
from django.conf import settings # 追記
from django.utils import timezone   # UTCで保存された日時を表示用に変換するため

def environment(**options):
    env = Environment(**options)

    def jst(value, fmt='%Y年%m月%d日 %H:%M'):
        """UTCで保存されている日時を、settings.TIME_ZONE（Asia/Tokyo）に直して整形する。
        USE_TZ=True のためDBの値はUTC。Django標準のテンプレートなら表示時に自動変換されるが、
        Jinja2 で .strftime() を直接呼ぶとその変換を通らず、UTCのまま（9時間前）表示される。"""
        if value is None:
            return ''
        return timezone.localtime(value).strftime(fmt)
    
    def url(viewname, *args, **kwargs):
        return reverse(viewname, args=args or None, kwargs=kwargs or None)

    env.globals.update({
        'static': static,
        'url': url,
        'jst': jst,   # 日時を日本時間に直して整形する（テンプレートから jst(値, '書式') で呼ぶ）
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
