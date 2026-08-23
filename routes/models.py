from django.db import models
from django.utils import timezone

from reports.models import Report
from users.models import SoftDeleteManager, AllObjectsManager, User

class Route(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='作成者')
    route_title = models.CharField(max_length=50, verbose_name='ルートタイトル')
    route_description = models.TextField(verbose_name='ルート本文')
    # ルートの位置情報（スタート地点）は不要なので削除
    # latitude = models.DecimalField(max_digits=10, decimal_places=8, verbose_name='緯度')
    # longitude = models.DecimalField(max_digits=11, decimal_places=8, verbose_name='経度')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='削除日時')

    # users/models.py で定義した共通マネージャーを利用
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ルート'
        verbose_name_plural = 'ルート一覧'
        db_table = 'routes'

    def __str__(self):
        return self.route_title

    @property
    def is_deleted(self):
        # deleted_atに値があれば「削除済み」と判定
        return self.deleted_at is not None

    # ルートの論理削除
    def delete(self, using=None, keep_parents=False):

        # ルートが論理削除されたら、中間テーブル（RouteReport）は物理削除することで、
        # どのルートにも使われていないレポートの削除が可能になる
        self.route_reports.all().delete()

        # deleted_atに現在時刻を代入
        self.deleted_at = timezone.now()
        # 更新日時（'updated_at'）には現在時刻を自動でセットされる
        self.save(update_fields=['deleted_at', 'updated_at'])

    # 物理削除用のメソッド(通常は使用しない）
    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


# 中間テーブル
# ルートかレポートのいずれかの紐づけが切れたら、物理削除される（deleted_atカラムを持たない）
class RouteReport(models.Model):

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='route_reports', verbose_name='ルート')

    # このレポートがルートに組み込まれている限り、物理削除が実行されてもProtectedErrorを出してブロックする
    # RouteReport行自体は物理削除されるので、ルートから外れれば自動的にこの制約も外れる
    report = models.ForeignKey(Report, on_delete=models.PROTECT, related_name='route_reports', verbose_name='レポート')

    sequence_order = models.BigIntegerField(verbose_name='並び順')

    class Meta:
        ordering = ['route', 'sequence_order']
        verbose_name = 'ルート・レポート'
        verbose_name_plural = 'ルート・レポート一覧'
        db_table = 'route_reports'

    def __str__(self):
        return f'{self.route} - {self.sequence_order}'


# ルートタグ
# 同じタグ名でも複数ユーザー（または同一ユーザー）が別レコードとして作成可能
class RouteTag(models.Model):
    tag_name =   models.CharField(max_length=50, verbose_name='タグ名')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='削除日時')

    # users/models.py で定義した共通マネージャーを利用
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ['tag_name']
        verbose_name = 'ルートタグ'
        verbose_name_plural = 'ルートタグ一覧'
        db_table = 'route_tags'

    def __str__(self):
        return self.tag_name
    
    @property
    def is_deleted(self):
        # deleted_atに値があれば「削除済み」と判定
        return self.deleted_at is not None

    # タグの論理削除
    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    # 物理削除用のメソッド(通常は使用しない）
    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


# 中間テーブル
# ルートかタグのいずれかの紐づけが切れたら、物理削除される（deleted_atカラムを持たない）
class RouteTagging(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='route_taggings', verbose_name='ルート')
    tag = models.ForeignKey(RouteTag, on_delete=models.CASCADE, related_name='route_taggings', verbose_name='タグ')

    class Meta:
        ordering = ['route', 'tag']
        verbose_name = 'ルート・タグ'
        verbose_name_plural = 'ルート・タグ一覧'
        db_table = 'route_taggings'
        # 同じルートに同じタグを二重付与できない制約
        unique_together = ('route', 'tag')

    def __str__(self):
        return f'{self.route} - {self.tag}'
