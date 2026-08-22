from django import forms
from .models import Route, RouteTag


class RouteForm(forms.ModelForm):
    # タグ入力欄
    # queryset=RouteTag.objects.all()は SoftDeleteManager経由なので、
    # 管理画面で論理削除（deleted_at設定）されたタグは選択肢に出てこない
    # 管理者が用意した既存タグから複数選択する
    tags = forms.ModelMultipleChoiceField(
        queryset=RouteTag.objects.all(),
        required=False, # タグ無しのルートも許可する
        widget=forms.SelectMultiple(attrs={ # 複数選択できるプルダウン
            "class": "form-control",
        }),
        label="タグ",
    )

    class Meta:
        model = Route # models.pyのRouteモデルを使用
        fields = [ # Routeモデルのこの2つのフィールドをフォームに表示してね
            "route_title",
            "route_description",
            ]

        widgets = {
            "route_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "ルートタイトルを入力"
            }),
            "route_description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "ルート本文を入力"
            }),
        }

