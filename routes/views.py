from django.shortcuts import render, get_object_or_404, redirect
from reports.models import Report
from .models import Route, RouteReport
from .forms import RouteForm


# ログイン済みかどうかチェック
def check_login(request):
    return 'user_id' in request.session


# 自分のルート一覧（ハンバーガーメニュ）
def myroute(request):
    if not check_login(request):
        return redirect('users:login')
    
    routes = Route.objects.filter(user_id=request.session.get('user_id'))
    return render(request, 'routes/myroute.html', {'routes': routes})


# ルート一覧画面（誰でも閲覧可能）
def route_list(request):
    routes = Route.objects.all()
    return render(request, 'routes/route_list.html', {'routes': routes})


# ルート詳細画面（誰でも閲覧可能）
def route_detail(request, pk):
    route = get_object_or_404(Route, pk=pk)
    return render(request, 'routes/route_detail.html', {'route': route})


# ルート作成のためのレポート選択画面
def route_select_reports(request):
    if not check_login(request):
        return redirect('users:login')

    if request.method == 'POST':
        # 選択されたレポートIDのリストをセッションに一時保存、作成画面へ引き継ぐ
        request.session['selected_report_ids'] = request.POST.getlist('report_ids')
        return redirect('routes:route_create')

    # 全てのレポートから選択
    reports = Report.objects.all()
    return render(request, 'routes/route_edit.html', {'reports': reports})


# ルート作成画面
def route_create(request):
    if not check_login(request):
        return redirect('users:login')

    # select_reportsで選んだレポートIDをセッションから取り出す
    report_ids = request.session.get('selected_report_ids', [])

    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            route = form.save(commit=False)
            route.user_id = request.session.get('user_id')
            route.save()

            # 選択されたレポートに順番を付けて中間テーブルに保存
            for order, report_id in enumerate(report_ids, start=1):
                RouteReport.objects.create(route=route, report_id=report_id, sequence_order=order)

            # 作成終了後、セッションに一時保存していたデータは削除
            if 'selected_report_ids' in request.session:
                del request.session['selected_report_ids']
            return redirect('routes:route_detail', pk=route.pk)
    else:
        form = RouteForm()

    # 選択済みのレポートの中身を画面に表示するために取得
    reports = Report.objects.filter(pk__in=report_ids)
    return render(request, 'routes/route_create.html', {'reports': reports, 'form': form})


# ルート編集画面
# GET:既存データが入ったフォームを用意
# POST:更新処理
def route_edit(request, pk):
    if not check_login(request):
        return redirect('users:login')
    
    route = get_object_or_404(Route, pk=pk)

    # 作成者以外は編集できない
    if str(route.user_id) != str(request.session.get('user_id')):
        return redirect('routes:route_detail', pk=route.pk)
    
    if request.method == 'POST':
        form = RouteForm(request.POST, instance=route)
        if form.is_valid():
            form.save()
            return redirect('routes:route_detail', pk=route.pk)
        # 無効な入力の場合、下のrenderで再表示する
    else:
        form = RouteForm(instance=route)    # GET時、既存データが入ったフォームを用意

    return render(request, 'routes/route_edit.html', {'route': route, 'form': form})


# ルート削除処理（POST専用）
def route_delete(request, pk):
    if not check_login(request):
        return redirect('users:login')

    route = get_object_or_404(Route, pk=pk)

    # 作成者以外は削除できない
    if str(route.user_id) != str(request.session.get('user_id')):
        return redirect('routes:route_detail', pk=route.pk)
    
    route.delete()
    return redirect('routes:myroute')
