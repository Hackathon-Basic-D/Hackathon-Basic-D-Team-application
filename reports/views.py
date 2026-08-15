from django.shortcuts import render, get_object_or_404, redirect
from .models import Report, ReportComment
from .forms import ReportForm


# ログイン済みかどうかチェック
def check_login(request):
    return 'user_id' in request.session


# 自分のレポート一覧（ハンバーガーメニュー)
def mypost(request):
    if not check_login(request):
        return redirect('users:login')  # 未ログインの場合、ログイン画面へ遷移

    # ログイン中のuser_idに紐づくレポートのみ取り込む    
    reports = Report.objects.filter(user_id=request.session.get('user_id'))
    return render(request, 'reports/mypost.html', {'reports': reports})


# レポート作成画面
# GET:フォーム表示
# POST:保存処理
def report_create(request):
    if not check_login(request):
            return redirect('users:login')
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            # commit=Falseで一旦DB保存せず、投稿者(user_id)をセットしてから保存する
            report = form.save(commit=False)
            report.user_id = request.session.get('user_id')
            report.save()
            return redirect('reports:report_detail', pk=report.pk)
        # form.is_valid()がFalseの場合、何もせずに下のrenderに進む
    else:
        form = ReportForm() # GETなら空のフォームを表示

    return render(request, 'reports/report_form.html', {'form': form})

# レポート詳細画面（未ログインでも閲覧可能）
def report_detail(request, pk):
    report = get_object_or_404(Report, pk=pk)   # 存在しないpkなら404エラー
    # テンプレート側でループ処理できるように、紐づくコメントも一緒に返す
    comments = ReportComment.objects.filter(report=report)
    return render(request, 'reports/report_detail.html', {'report': report, 'comments': comments})


# レポート編集画面
# GET:フォーム表示
# POST:更新処理
def report_edit(request, pk):
    if not check_login(request):
        return redirect('users:login')

    report = get_object_or_404(Report, pk=pk)

    # レポート作成者以外は編集できない（詳細画面へ遷移）
    if str(report.user_id) != str(request.session.get('user_id')):
        return redirect('reports:report_detail', pk=report.pk)
    
    if request.method == 'POST':
        # instance=reportを渡すことで「既存レコードの更新」として扱う
        form = ReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            return redirect('reports:report_detail', pk=report.pk)
    else:
        form = ReportForm(instance=report)  # 既存の値が入ったフォームを表示

    return render(request, 'reports/report_form.html', {'report': report, 'form': form})


# レポート削除処理(画面は持たない）
def report_delete(request, pk):
    if not check_login(request):
        return redirect('users:login')
    
    report = get_object_or_404(Report, pk=pk)

    # 投稿者以外は削除できない
    if str(report.user_id) != str(request.session.get('user_id')):
        return redirect('reports:report_detail', pk=report.pk)
    
    report.delete() # models.pyで論理削除にオーバーライド
    return redirect('reports:mypost')


# コメント作成処理(POST専用、レポート詳細画面のモーダル）
def comment_create(request, pk):
    if not check_login(request):
        return redirect('users:login')
    
    report = get_object_or_404(Report, pk=pk)
    comment_text = request.POST.get('report_comment')

    # 空文字・空白のコメントは保存しない
    if comment_text and comment_text.strip():
        ReportComment.objects.create(
            report=report,
            user_id=request.session.get('user_id'),
            report_comment=comment_text,
        )

    # 投稿してもしなくても、レポート詳細画面へ遷移
    return redirect('reports:report_detail', pk=report.pk)


# コメント削除処理(POST専用)
def comment_delete(request, pk):
    if not check_login(request):
        return redirect('users:login')
    
    comment = get_object_or_404(ReportComment, pk=pk)
    report_pk = comment.report_id   # コメント削除後、どのレポート詳細へ戻るか記憶しておく

    # コメント作成者以外は削除できない
    if str(comment.user_id) != str(request.session.get('user_id')):
        return redirect('reports:report_detail', pk=report_pk)
    
    comment.delete()
    return redirect('reports:report_detail', pk=report_pk)
