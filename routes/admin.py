from django.contrib import admin
from .models import Route, RouteReport, RouteTag, RouteTagging


# ルート編集画面の中に「このルートに含まれるレポート(順番付き)」を埋め込む
class RouteReportInline(admin.TabularInline):
    model = RouteReport
    extra = 0
    fields = ('report', 'sequence_order')
    ordering = ('sequence_order',)


# ルート編集画面の中に「このルートに紐づいているタグ」を埋め込む
class RouteTaggingInline(admin.TabularInline):
    model = RouteTagging
    extra = 0
    fields = ('tag',)
    autocomplete_fields = ('tag',) # タグが増えても検索して選べるように


# 論理削除されたレコードを復元する共通アクション
# Route/RouteTagの両方のManagerで使い回す
@admin.action(description='選択した項目を復元する（論理削除を解除）')
def restore_selected(modeladmin, request, queryset):
    queryset.update(deleted_at=None)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    # テーブルに表示するカラム
    list_display = ('route_title', 'user', 'is_deleted', 'created_at', 'updated_at')
    # ページ右サイドバーの絞り込み用フィルタ：削除済み/未削除で絞り込めるように
    list_filter = ('deleted_at',)
    # 検索ボックス：タグ名でもルートを検索できるように
    search_fields = ('user__user_name', 'route_title', 'route_taggings__tag__tag_name')
    date_hierarchy = 'created_at'
    # 自動セットされる日時は手入力させない
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    inlines = [RouteReportInline, RouteTaggingInline]
    actions = [restore_selected]

    # デフォルトのRoute.objects（SoftDeleteManager）だと削除済みが一覧から消えてしまうため、
    # all_objectsを使って削除済みも表示し、is_deleted列とフィルタで区別できるようにする
    def get_queryset(self, request):
        return Route.all_objects.select_related('user').all()

    @admin.display(description='削除済み', boolean=True)
    def is_deleted(self, obj):
        return obj.is_deleted


@admin.register(RouteReport)
class RouteReportAdmin(admin.ModelAdmin):
    # テーブルに表示するカラム
    list_display = ('route', 'report', 'sequence_order')
    # ページ右サイドバーの絞り込み用フィルタ
    list_filter = ()
    # 検索ボックス
    search_fields = ('route__route_title', 'report__report_title',)
    ordering = ('route', 'sequence_order')


@admin.register(RouteTag)
class RouteTagAdmin(admin.ModelAdmin):
    list_display = ('tag_name', 'route_count', 'is_deleted', 'created_at')
    list_filter = ('deleted_at',)
    search_fields = ('tag_name',)
    actions = [restore_selected]

    # 削除済みタグも復元できるようにする
    def get_queryset(self, request):
        return RouteTag.all_objects.all()

    @admin.display(description='削除済み', boolean=True)
    def is_deleted(self, obj):
        return obj.is_deleted

    @admin.display(description='利用ルート数')
    def route_count(self, obj):
        #　このタグが何件のルートに使われているか
        return obj.route_taggings.count()

@admin.register(RouteTagging)
class RouteTaggingAdmin(admin.ModelAdmin):
    list_display = ('route', 'tag')
    list_filter =('tag',)
    search_fields = ('route__route_title', 'tag__tag_name')
    autocomplete_fields = ('route', 'tag')
