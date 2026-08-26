// コメントの作成・編集・削除を、ページ遷移せず（AJAXで）行い、コメント一覧だけ更新する
// ＝コメント画面が閉じない／開き直しのアニメも発生しない
(function () {
    var OC = '#offcanvasBottom';

    // 返ってきた詳細ページHTMLから、コメント一覧の中身だけ差し替える
    function refreshList(html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var neu = doc.querySelector(OC + ' .offcanvas-body');
        var cur = document.querySelector(OC + ' .offcanvas-body');
        if (neu && cur) { cur.innerHTML = neu.innerHTML; }
    }

    // 401（ログインしていない／切れている）を受けたときに未ログイン時の表示と同じ状態にする
    function lockCommentForm() {
        var footer = document.querySelector(OC + ' .comment-footer');
        if (!footer) { return; }
        var hint = footer.querySelector('.comment-login-hint');
        if (hint) { hint.hidden = false; }
        var input = footer.querySelector('input[name="report_comment"]');
        if (input) { input.disabled = true; }
        var send = footer.querySelector('.comment-send');
        if (send) { send.disabled = true; }
    }

    // フォームをAJAX送信し、成功したら一覧を更新
    function ajaxSubmit(form, done) {
        fetch(form.getAttribute('action') || location.href, {
            method: 'POST',
            body: new FormData(form),                      // csrf_input のトークンも含まれる
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin'
        })
            .then(function (r) {
                // サーバーが401を返したら「ログインしていない／切れている」
                // ここで止めないと、リダイレクト先のログイン画面のHTMLを受け取ってしまい、コメント欄が見つからず一覧も更新されないまま、入力だけ消える状態になる
                if (r.status === 401) {
                    lockCommentForm();
                    return null;                           // 後続で処理を打ち切るための合図
                }
                return r.text();
            })
            .then(function (html) {
                if (html === null) { return; }             // 401だったので一覧の更新はしない
                refreshList(html);
                if (done) done();
            })
            .catch(function () { form.submit(); });        // 通信自体に失敗したときは通常送信にフォールバック
    }

    // コメント画面内のフォーム送信をAJAX化（作成・編集・削除）
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form.closest(OC)) return;                     // コメント画面内だけ対象
        e.preventDefault();
        if (form.classList.contains('comment-delete')) {   // 削除は確認カードを挟む
            window.appConfirm('コメントを削除しますか？', function () { ajaxSubmit(form); });
        } else {                                           // 作成・編集はそのままAJAX
            ajaxSubmit(form, function () {
                var input = form.querySelector('input[name="report_comment"]');
                if (input) { input.value = ''; }           // 作成フォームの入力をクリア
            });
        }
    });
})();