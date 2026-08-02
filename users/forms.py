from django import forms
from .models import User # models.pyからUserモデルをインポート

# ユーザー管理機能で使用するフォームを定義
# HTML側では {{ form.フィールド名 }} や {{ field }} で表示される

class SignUpForm(forms.ModelForm):# 新規登録画面フォーム(ModelForm:DBに保存・更新するためのフォーム)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "パスワードを入力"
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "もう一度入力してください"
        })
    )

    class Meta:
        model = User # models.pyのUserモデルを使用
        fields = [
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
            "main_area": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "メインエリアを入力"
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

class LoginForm(forms.Form):# ログイン画面フォーム(Form:入力を受け取るだけ＝views.pyがDBと照合する)
    user_name = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "ユーザー名を入力"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "パスワードを入力"
        })
    )

class UserEditForm(SignUpForm):# ユーザー情報編集画面フォーム(SignUpFormを継承) 
    pass# SignUpFormをそのまま使います。追加なしです。passは空の処理を意味する。