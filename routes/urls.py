from django.urls import path
from . import views

app_name = 'routes'

urlpatterns = [
    path('',                      views.route_list,           name='route_list'),           # ルート一覧画面
    path('create/',               views.route_create,         name='route_create'),         # ルート記事作成画面
    path('create/select_reports', views.route_select_reports, name='route_select_reports'), # ルート用レポート選択画面
    path('<int:pk>/',             views.route_detail,         name='route_detail'),         # ルート詳細画面
    path('<int:pk>/edit/',        views.route_edit,           name='route_edit'),           # ルート編集画面
    path('<int:pk>/delete/',      views.route_delete,         name='route_delete'),         # ルート詳細画面（削除）
]
