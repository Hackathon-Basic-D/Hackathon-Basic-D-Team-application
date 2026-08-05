from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [    
    path('create/',            views.report_create,  name='report_create'),     # レポート作成画面
    path('<int:pk>/',          views.report_detail,  name='report_detail'),     # レポート詳細画面
    path('<int:pk>/edit/',     views.report_edit,    name='report_edit'),       # レポート編集画面
    path('<int:pk>/delete/',   views.report_delete,  name='report_delete'),     # レポート削除
    path('<int:pk>/comments/', views.comment_create, name='comment_create'),    # レポート詳細画面コメント投稿
]
