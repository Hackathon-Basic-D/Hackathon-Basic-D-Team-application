from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('reports/', include('reports.urls')),
    path('routes/', include('routes.urls')),
    path('spots/', include('spots.urls')),      # スポット一覧
]

# DEBUG=True（開発環境）のときだけ、アップロードされた画像をDjangoに配信させる
# 本番運用時（DEBUG＝True）はS3やnginx等が画像配信を担当するため、
# このstatic()は暫定処理とする
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Django がエラーを検知したときに呼ぶビューの指定
# ルートURLconf（settings.py の ROOT_URLCONF が指すモジュール）に、この名前の変数として書かないと認識されない（users/urls.py に書いても効かない）
# DEBUG=True のあいだは常にトレースバック画面が出るため、これらは使われない
handler400 = 'users.views.error400'
handler404 = 'users.views.error404'
handler500 = 'users.views.error500'
