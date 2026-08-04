from django.contrib import admin
from django.urls import path
from routes.views import welcome, home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', welcome, name='welcome'),
    path('home/', home, name='home'),
]
