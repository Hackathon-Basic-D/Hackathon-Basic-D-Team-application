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

    // フォームをAJAX送信し、成功したら一覧を更新
    function ajaxSubmit(form, done) {
        fetch(form.getAttribute('action') || location.href, {
            method: 'POST',
            body: new FormData(form),                      // csrf_input のトークンも含まれる
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin'
        })
            .then(function (r) { return r.text(); })
            .then(function (html) { refreshList(html); if (done) done(); })
            .catch(function () { form.submit(); });        // 失敗時は通常送信にフォールバック
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