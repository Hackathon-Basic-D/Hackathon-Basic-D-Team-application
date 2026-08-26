from django import forms
from .models import Report # models.pyからReportモデルをインポート
from .models import ReportComment # models.pyからReportCommentモデルをインポート

from users.regions import strip_region_prefix   # 編集時にタイトルから地域ラベルを外すため

# タイトルに入力できる最大文字数
TITLE_MAX_LENGTH = 50

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
        fields = [# Reportモデルのこのフィールドをフォームに表示してね
            "report_title",
            "report_description",
            "latitude",       # 地図クリックで取得した緯度（hiddenで保持）
            "longitude",      # 地図クリックで取得した経度（hiddenで保持）
        ]
        widgets = {# HTML側で {{ field }} や {{ form.report_title }} を表示したときの見た目を設定
            "report_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "レポートタイトルを入力",
                "maxlength": TITLE_MAX_LENGTH,   # ブラウザ側の入力制限（サーバー側の検証は clean_report_title）
            }),
            "report_description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": " レポート本文を入力",
                "rows": 4,
            }),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }
    # 編集画面では、タイトルから先頭の地域ラベル【…】を外して入力欄に表示
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)                      # 通常のフォーム初期化
        if self.instance and self.instance.pk:                 # 既存レコードの編集のときだけ
            self.initial['report_title'] = strip_region_prefix(self.instance.report_title)

    # タイトルの長さチェック：
    # 保存時に Report.save() が先頭へ地域ラベルを付けるため、モデル由来の50文字まで入力させると、検証を通った後にカラム長を超えてしまう
    # ラベルは自動で付くものなので、ユーザーが入力できるのは本文のみ40文字とする
    def clean_report_title(self):
        title = self.cleaned_data.get('report_title', '')                  # フィールド検証を通ったタイトルを取り出す
        if len(title) > TITLE_MAX_LENGTH:                                  # 上限を超えていたら
            raise forms.ValidationError(f'タイトルは{TITLE_MAX_LENGTH}文字以下で入力してください。')  # エラーにする
        return title                                                       # 問題なければそのまま返す
    
    # 緯度の範囲チェック：有効範囲(-90〜90)の外は不正として弾く。
    # 要件「座標はクライアント由来で信用しない／サーバ側で範囲チェック」への対応。
    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')            # フィールド検証を通った緯度の値を取り出す
        if lat is not None and not (-90 <= lat <= 90):     # 値があり、かつ緯度の有効範囲外なら
            raise forms.ValidationError('緯度が範囲外です。')  # エラーにする（画面のエラー表示に出る）
        return lat                                         # 問題なければそのまま返す（cleaned_dataに戻る）

    # 経度の範囲チェック：有効範囲(-180〜180)の外は不正として弾く。
    def clean_longitude(self):
        lng = self.cleaned_data.get('longitude')           # フィールド検証を通った経度の値を取り出す
        if lng is not None and not (-180 <= lng <= 180):   # 値があり、かつ経度の有効範囲外なら
            raise forms.ValidationError('経度が範囲外です。')  # エラーにする
        return lng                                         # 問題なければそのまま返す

    # タイトルはモデル由来の 50 文字ではなく 40 文字を上限にする。
    # 保存時に Report.save() が先頭へ【神奈川県】など最長6文字の地域ラベルを付けるため、
    # 50 のままだと検証を通った後に超過してしまう（40 + 6 = 46 ≦ 50）。
    # 地域ラベルは自動で付くものなので、ユーザーが入力するのは本文だけとして扱う。
    report_title = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "レポートタイトルを入力（40文字まで）",
        }),
    )


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