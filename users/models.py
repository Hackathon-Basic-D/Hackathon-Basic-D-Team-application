import uuid

from django.contrib.auth.hashers import check_password, make_password   # ハッシュ化に使用
from django.db import models
from django.utils import timezone   # 時刻取得用


# User/Report/Route共通の論理削除用クエリセット
class SoftDeleteQuerySet(models.QuerySet):

    # 実際にはDELETE文は発行せず、UPDATEで上書き
    def delete(self):
        update_fields = {'deleted_at': timezone.now()}
        # updated_atフィールドを持つモデル(User/Report/Route)だけ、一緒に更新する
        if any(f.name == 'updated_at' for f in self.model._meta.fields):
            update_fields['updated_at'] = timezone.now()
        return self.update(**update_fields)

    # 物理削除したい時に使用（通常は使用しない）
    def hard_delete(self):
        return super().delete()


# 〇〇.objects で、論理削除されていないレコードのみ返す共通マネージャー
class SoftDeleteManager(models.Manager):

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


# 〇〇.all_objects で、削除済みも含めて全件を返す共通マネージャー
class AllObjectsManager(models.Manager):

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class User(models.Model):
    id =         models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ユーザーID',)
    user_name =  models.CharField(max_length=50, verbose_name='ユーザー名')
    email =      models.EmailField(max_length=255, unique=True, verbose_name='メールアドレス')
    password_hash = models.CharField(max_length=255, verbose_name='パスワードハッシュ')
    main_area =  models.CharField(max_length=50, default='Tokyo', verbose_name='メインエリア')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='削除日時')

    # マネージャーの設定
    objects = SoftDeleteManager()       # 削除済みユーザーを除外
    all_objects = AllObjectsManager()   # 削除済みユーザーを含めた全件

    # 管理画面用
    class Meta:
        ordering = ['-created_at']             # 新しく作成された順に並べる
        verbose_name = 'ユーザー'               # 管理画面での単数形の表示名
        verbose_name_plural = 'ユーザー一覧'    # 管理画面での複数形(一覧）の表示名
        db_table = 'users'

    def __str__(self):
        # 管理画面やシェルではID(UUID)ではなく名前を表示
        return self.user_name

    # パスワードをハッシュ化して保存
    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    @property
    def is_deleted(self):
        # deleted_atに値があれば「削除済み」と判定
        return self.deleted_at is not None

    # ユーザーの論理削除
    def delete(self, using=None, keep_parents=False):

        # どのルートにも使われていないレポート（route_reportsが空の）は、ユーザーと一緒に論理削除
        for report in self.report_set.filter(route_reports__isnull=True):
            report.delete()

        # いずれかのルートに使われているレポートは、ユーザが削除されても削除しない
        # userをNULLにする(updated_atも更新)
        self.report_set.filter(route_reports__isnull=False).update(user=None, updated_at=timezone.now())

        # ユーザが削除されると、そのユーザーが作成した全てのルートは論理削除する
        for route in self.route_set.all():
            route.delete()

        # deleted_atに現在時刻を代入
        self.deleted_at = timezone.now()
        # 更新日時（'updated_at'）には現在時刻を自動でセットされる
        self.save(update_fields=['deleted_at', 'updated_at'])

    # 物理削除用のメソッド(通常は使用しない）
    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)
