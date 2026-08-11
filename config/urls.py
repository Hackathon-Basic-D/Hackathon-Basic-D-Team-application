from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('reports/', include('reports.urls')),
    path('routes/', include('routes.urls')),
]
