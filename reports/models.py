from django.db import models
from django.db.models import ProtectedError
from django.utils import timezone

from users.models import SoftDeleteManager, AllObjectsManager, User
from users.regions import prefecture_of, with_region_prefix

# ＜レポートテーブル＞
# Userが論理削除されても、Reportは削除されない(論理削除）
# Userが削除された場合、UserはNULLに設定される
class Report(models.Model):
    user =  models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ユーザー')
    report_title = models.CharField(max_length=50, verbose_name='レポートタイトル')
    report_description = models.TextField(verbose_name='レポート本文')
    latitude =  models.DecimalField(max_digits=10, decimal_places=8, verbose_name='緯度')
    longitude = models.DecimalField(max_digits=11, decimal_places=8, verbose_name='経度')
    report_image_url = models.CharField(max_length=255, blank=True, null=True, verbose_name='画像URL')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='削除日時')

    # users/models.py で定義した共通マネージャーを利用
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'レポート'
        verbose_name_plural = 'レポート一覧'
        db_table = 'reports'

    def __str__(self):
        return self.report_title

    # タイトル先頭の地域ラベルを、保存経路（view・admin・shell 等）に関係なく必ず付けるための共通処理。
    # view だけに書くと Django admin 等は素通りするため、モデルの save に集約する。
    def save(self, *args, **kwargs):
        # 論理削除など report_title を更新しない保存（update_fields 指定）ではスキップする
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'report_title' in update_fields:
            # 座標から都道府県を判定し、先頭の既存【…】を外して付け直す（大阪→大阪府 の正規化にもなる）
            self.report_title = with_region_prefix(
                self.report_title,
                prefecture_of(self.latitude, self.longitude),
            )
        super().save(*args, **kwargs)

    @property
    def is_deleted(self):
        # deleted_atに値があれば「削除済み」と判定
        return self.deleted_at is not None

    # レポートの論理削除
    def delete(self, using=None, keep_parents=False):

        # ルートに組み込まれているレポートは削除不可（ルートから外れれば削除できる）
        route_reports = self.route_reports.all()
        if route_reports.exists():
            raise ProtectedError(
                'このレポートはルートに使われているため削除できません。',
                route_reports,
            )

        # レポートが論理削除されたら、それに紐づく全てのレポートコメントも論理削除される
        self.comments.all().delete()

        # deleted_atに現在時刻を代入
        self.deleted_at = timezone.now()
        # 更新日時（'updated_at'）には現在時刻を自動でセットされる
        self.save(update_fields=['deleted_at', 'updated_at'])

    # 物理削除用のメソッド(通常は使用しない）
    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


# ＜レポートコメントテーブル＞
class ReportComment(models.Model):
    # レポートが削除されると、レポートコメントも削除される
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='comments', verbose_name='レポート')
    user =   models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='ユーザー')
    report_comment = models.TextField(verbose_name='レポートコメント')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='削除日時')

    # マネージャーの設定
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    # 管理画面用
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'レポートコメント'
        verbose_name_plural = 'レポートコメント一覧'
        db_table = 'report_comments'

    def __str__(self):
        return f'{self.user} のコメント({self.report})'

    @property
    def is_deleted(self):
        # deleted_atに値があれば「削除済み」と判定
        return self.deleted_at is not None

    # レポートコメントの論理削除
    def delete(self, using=None, keep_parents=False):

        # deleted_atに現在時刻を代入
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    # 物理削除用のメソッド(通常は使用しない）
    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


# ＜レポートのタグ＞
# 同じタグ名でも複数ユーザー（または同一ユーザー）が別レコードとして作成可能
class ReportTag(models.Model):
    tag_name = models.CharField(max_length=50, verbose_name='タグ名')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='削除日時')

    # users/models.py で定義した共通マネージャーを利用
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ['tag_name']
        verbose_name = 'レポートタグ'
        verbose_name_plural = 'レポートタグ一覧'
        db_table = 'report_tags'

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


# ＜レポートタグ中間テーブル＞
# レポートがタグのいずれかの紐づけが切れたら物理削除される（deleted_atカラムを持たない）
class ReportTagging(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE,
                               related_name='report_taggings', verbose_name='レポート')
    tag = models.ForeignKey(ReportTag, on_delete=models.CASCADE,
                            related_name='report_taggings', verbose_name='タグ')

    class Meta:
        ordering = ['report', 'tag']
        verbose_name = 'レポート・タグ'
        verbose_name_plural = 'レポート・タグ一覧'
        db_table = 'report_taggings'
        # 同じレポートに同じタグを二重付与できない制約
        unique_together = ('report', 'tag')

    def __str__(self):
        return f'{self.report} - {self.tag}'
