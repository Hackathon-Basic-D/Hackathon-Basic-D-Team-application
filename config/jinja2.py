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
