from django.urls import path
from . import views

app_name = 'spots'

urlpatterns = [
    path('', views.spot_list, name='spot_list'),   # スポット一覧画面
    path('<str:pk>/', views.spot_detail, name='spot_detail'),  # スポット詳細画面
]