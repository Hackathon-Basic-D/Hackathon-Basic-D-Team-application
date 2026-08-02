from django.contrib import admin
from .models import Route, RouteReport


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    # テーブルに表示するカラム
    list_display = ('user', 'route_title', 'route_description', 'created_at')
    # ページ右サイドバーの絞り込み用フィルタ
    list_filter = ()
    # 検索ボックス
    search_fields = ('user__user_name', 'route_title')


@admin.register(RouteReport)
class RouteReportAdmin(admin.ModelAdmin):
    # テーブルに表示するカラム
    list_display = ('route', 'report')
    # ページ右サイドバーの絞り込み用フィルタ
    list_filter = ()
    # 検索ボックス
    search_fields = ('report__report_title',)
