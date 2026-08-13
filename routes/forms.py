from django import forms
from .models import Route # models.pyからRouteモデルをインポート

#
class RouteForm(forms.ModelForm):

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
            "route_description": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "ルート本文を入力"
            }),
        }

