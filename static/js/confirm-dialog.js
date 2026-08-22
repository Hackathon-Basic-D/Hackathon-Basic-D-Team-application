// アプリ独自の確認カード（ブラウザ confirm() の代わり）
// - data-confirm="メッセージ" 付きフォーム：送信を横取りしてカード表示（通常送信用）
// - window.appConfirm(メッセージ, OK時の関数)：プログラムから確認カードを出す（AJAX用）
(function () {
    var overlay = document.createElement("div");
    overlay.className = "confirm-overlay";
    overlay.innerHTML =
        '<div class="card-box confirm-box">' +
        '  <p class="confirm-message"></p>' +
        '  <div class="confirm-actions">' +
        '    <button type="button" class="confirm-cancel">いいえ</button>' +
        '    <button type="button" class="confirm-ok">はい</button>' +
        '  </div>' +
        '</div>';
    document.body.appendChild(overlay);
    var msgEl = overlay.querySelector(".confirm-message");
    var onOk = null;

    function open(message, ok) {
        onOk = ok;
        msgEl.textContent = message || "実行しますか？";
        overlay.classList.add("show");
    }
    function close() { overlay.classList.remove("show"); onOk = null; }

    overlay.querySelector(".confirm-ok").addEventListener("click", function () {
        var cb = onOk; close(); if (cb) cb();
    });
    overlay.querySelector(".confirm-cancel").addEventListener("click", close);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });

    // プログラムから使う公開API（例：comment.js のコメント削除）
    window.appConfirm = function (message, ok) { open(message, ok); };

    // data-confirm 付きフォームの自動対応（通常送信用：例 レポート削除）
    document.addEventListener("submit", function (e) {
        var f = e.target;
        if (f.hasAttribute("data-confirm") && f.dataset.confirmed !== "1") {
            e.preventDefault();
            open(f.getAttribute("data-confirm"), function () {
                f.dataset.confirmed = "1";
                if (f.requestSubmit) { f.requestSubmit(); } else { f.submit(); }
            });
        }
    }, true);
})();