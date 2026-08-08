from django.contrib import admin
from django.urls import path, include

from reports import views as report_views
from routes import views as route_views


urlpatterns = [
    path('admin/', admin.site.urls),    # 管理画面

    # 各アプリケーションのURL
    path('', include('users.urls')),            # usersアプリに引き継ぎ
    path('reports/', include('reports.urls')),  # reportsアプリに引き継ぎ
    path('comments/<int:pk>/delete/', report_views.comment_delete, name='comment_delete'),  # レポートのコメント削除、直接呼び出し
    path('routes/', include('routes.urls')),    # routesアプリに引き継ぎ

    path('myreports/', report_views.mypost, name='mypost'), # 作成済みレポート一覧（ハンバーガーメニュー）、直接呼び出し
    path('myroutes/', route_views.myroute, name='myroute'), # 作成済みルート一覧画面（ハンバーガーメニュー）、直接呼び出し
]

handler400 = 'users.views.error400'
handler404 = 'users.views.error404'
handler500 = 'users.views.error500'
