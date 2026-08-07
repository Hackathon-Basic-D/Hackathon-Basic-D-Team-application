from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.welcome, name='welcome'),            # ウェルカム画面
    path('signup/', views.signup_view,  name='signup'), # 新規登録画面
    path('login/',  views.login_view,   name='login'),  # ログイン画面
    path('logout/', views.logout_view,  name='logout'), # ログアウト処理
    path('home/',   views.home,         name='home'),   # ホーム画面
    path('settings/',   views.setting,  name='setting'),    # 設定画面（ハンバーガーメニュー）

    path('error400/',   views.error400, name='error400'),
    path('error404/',   views.error404, name='error404'),
    path('error500/',   views.error500, name='error500'),
]
