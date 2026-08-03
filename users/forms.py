from django import forms
from .models import User # models.pyからUserモデルをインポート

# ユーザー管理機能で使用するフォームを定義
# HTML側では {{ form.フィールド名 }} や {{ field }} で表示される

PREFECTURE_CHOICES = [
    ("Hokkaido", "北海道"),
    ("Aomori", "青森県"),
    ("Iwate", "岩手県"),
    ("Miyagi", "宮城県"),
    ("Akita", "秋田県"),
    ("Yamagata", "山形県"),
    ("Fukushima", "福島県"),
    ("Ibaraki", "茨城県"),
    ("Tochigi", "栃木県"),
    ("Gunma", "群馬県"),
    ("Saitama", "埼玉県"),
    ("Chiba", "千葉県"),
    ("Tokyo", "東京都"),
    ("Kanagawa", "神奈川県"),
    ("Niigata", "新潟県"),
    ("Toyama", "富山県"),
    ("Ishikawa", "石川県"),
    ("Fukui", "福井県"),
    ("Yamanashi", "山梨県"),
    ("Nagano", "長野県"),
    ("Gifu", "岐阜県"),
    ("Shizuoka", "静岡県"),
    ("Aichi", "愛知県"),
    ("Mie", "三重県"),
    ("Shiga", "滋賀県"),
    ("Kyoto", "京都府"),
    ("Osaka", "大阪府"),
    ("Hyogo", "兵庫県"),
    ("Nara", "奈良県"),
    ("Wakayama", "和歌山県"),
    ("Tottori", "鳥取県"),
    ("Shimane", "島根県"),
    ("Okayama", "岡山県"),
    ("Hiroshima", "広島県"),
    ("Yamaguchi", "山口県"),
    ("Tokushima", "徳島県"),
    ("Kagawa", "香川県"),
    ("Ehime", "愛媛県"),
    ("Kochi", "高知県"),
    ("Fukuoka", "福岡県"),
    ("Saga", "佐賀県"),
    ("Nagasaki", "長崎県"),
    ("Kumamoto", "熊本県"),
    ("Oita", "大分県"),
    ("Miyazaki", "宮崎県"),
    ("Kagoshima", "鹿児島県"),
    ("Okinawa", "沖縄県"),
]

# 新規登録画面フォーム(ModelForm:DBに保存・更新するためのフォーム)
class SignUpForm(forms.ModelForm):

    # Userモデルにはmain_areaフィールドはあるが、ChoiceFieldで都道府県を選択するようにするため、フォーム側で上書きする
    main_area = forms.ChoiceField(        
        choices=PREFECTURE_CHOICES,
        label="メインエリア",
        initial="Osaka",
        widget=forms.Select(attrs={
            "class": "form-select",
        })
    )

    # Userモデルのpasswordを入力するためのフォーム項目
    # 保存時にset_password()でハッシュ化してDBへ保存する
    password = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "パスワードを入力"
        })
    )
    
    # Userモデルにはpassword_confirmフィールドはないので、フォーム側で定義する
    password_confirm = forms.CharField(
        label="パスワード（確認）",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "もう一度入力してください"
        })
    )

    class Meta:
        model = User # models.pyのUserモデルを使用
        fields = [# 「Userモデルのこの3つのフィールドをフォームに表示してね」
            "user_name",
            "email",
            "main_area",
        ]
        widgets = {# HTML側で {{ field }} や {{ form.user_name }} を表示したときの見た目を設定
            "user_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "ユーザー名を入力"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "メールアドレスを入力"
            }),
        }

    # パスワード一致チェック
    def clean(self):# clean(self)はDjangoの入力チェック関数
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password != password_confirm:
            raise forms.ValidationError("パスワードが一致しません。")

        return cleaned_data

    # 保存処理
    def save(self, commit=True):
        user = super().save(commit=False)

        # models.py の set_password() を利用
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        return user
# commitはDBに保存するかどうかを決めるフラグ
# commit=False にすることで、一旦DBへ保存せず Userオブジェクトだけ作成する
# その後、set_password()でパスワードをハッシュ化し、最後にuser.save()でDBへ保存する

# ログイン画面フォーム(Form:入力を受け取るだけ＝views.pyがDBと照合する)
class LoginForm(forms.Form):
    email = forms.CharField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "メールアドレスを入力"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "パスワードを入力"
        })
    )

# ユーザー情報編集画面フォーム(SignUpFormを継承) 
class UserEditForm(SignUpForm):
    pass# SignUpFormをそのまま使います。追加なしです。passは空の処理を意味する。