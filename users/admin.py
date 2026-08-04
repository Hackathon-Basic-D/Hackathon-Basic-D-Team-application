from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # テーブルに表示するカラム
    list_display = ('user_name', 'email', 'main_area', 'created_at')
    # ページ右サイドバーの絞り込み用フィルタ
    list_filter = ('main_area',)
    # 検索ボックス
    search_fields = ('username', 'main_area')
