from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView # 追記
import os # 追記


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='welcome.html'), name='welcome'), # 追記
    path('home/', TemplateView.as_view(template_name='home.html', extra_context={'google_maps_api_key': os.environ.get('GOOGLE_MAPS_API_KEY_FRONT', '')}), name='home'), # 追記
]
