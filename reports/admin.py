from django.contrib import admin
from .models import Report, ReportComment


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    # テーブルに表示するカラム
    list_display = ('report_title', 'report_description', 'report_image_url', 'created_at')
    # ページ右サイドバーの絞り込み用フィルタ
    list_filter = ()
    # 検索ボックス
    search_fields = ('report_title',)


@admin.register(ReportComment)
class ReportCommentAdmin(admin.ModelAdmin):
    # テーブルに表示するカラム
    list_display = ('report', 'user', 'report_comment', 'created_at')
    # ページ右サイドバーの絞り込み用フィルタ
    list_filter = ('user',)
    # 検索ボックス
    search_fields = ('report__report_title',)
