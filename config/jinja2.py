from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment


def environment(**options):
    env = Environment(**options)

    def url(viewname, *args, **kwargs):
        return reverse(viewname, args=args or None, kwargs=kwargs or None)

    env.globals.update({
        'static': static,
        'url': url,
    })
    return env