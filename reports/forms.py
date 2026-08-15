from django import forms
from .models import Report # models.pyからReportモデルをインポート
from .models import ReportComment # models.pyからReportCommentモデルをインポート

#　レポート記事作成フォーム
class ReportForm(forms.ModelForm):
# ユーザーが投稿する画像ファイルを受け取るためのフィールド
# S3へアップロードする画像を一時的に受け取るために使用（DBのカラムにはS3のURLしか保存しないから）
# Djangoで画像を受け取るためには、forms.ImageField()を使用する必要がある
    report_image = forms.ImageField(
        required=False, # 画像は必須ではない。(DB設計のnull=Trueより）画像なしでもフォーム送信できる。
        widget=forms.ClearableFileInput(attrs={ #画像の選択や変更ができるウィジェットを使用
            "class": "form-control",
        })
    )

    class Meta:
        model = Report # models.pyのReportモデルを使用
        fields = [# Reportモデルのこの2つのフィールドをフォームに表示してね
            "report_title",
            "report_description",       
        ]
        widgets = {# HTML側で {{ field }} や {{ form.report_title }} を表示したときの見た目を設定
            "report_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "レポートタイトルを入力"
            }),
            "report_description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": " レポート本文を入力"
            }),
        }

#   レポートコメント作成フォーム
class ReportCommentForm(forms.ModelForm):
    class Meta:
        model = ReportComment # models.pyのReportCommentモデルを使用
        fields = [# ReportCommmentモデルのこの１つのフィールドをフォームに表示してね]
            "report_comment",
        ]
        widgets = {# HTML側で {{ field }} や {{ form.report_comment }} を表示したときの見た目を設定
            "report_comment": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "コメントを入力"
            }),
        }