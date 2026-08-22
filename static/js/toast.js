// アプリ独自のお知らせトースト。window.showToast("メッセージ") で画面下部に数秒表示。
(function () {
    var toast = document.createElement("div");
    toast.className = "app-toast";
    document.body.appendChild(toast);
    var timer = null;
    window.showToast = function (message) {
        toast.textContent = message;
        toast.classList.add("show");
        clearTimeout(timer);
        timer = setTimeout(function () { toast.classList.remove("show"); }, 3000);
    };
})();