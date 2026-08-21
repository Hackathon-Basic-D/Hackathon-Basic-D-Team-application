// 未ログイン時、ログインが必要な操作（.needs-login）をタップしたら、
// 画面遷移させず、その場にメッセージ（ログインリンク付き）を出す
(function () {
    const links = document.querySelectorAll(".needs-login");
    if (!links.length) return;   // 対象が無ければ何もしない

    // メッセージ表示用のトーストを1つ用意
    const toast = document.createElement("div");
    toast.className = "login-toast";
    document.body.appendChild(toast);
    let timer = null;

    links.forEach((el) => {
        el.addEventListener("click", (e) => {
            e.preventDefault();   // 遷移させない（home等の地図を再読み込みさせない）
            // 「ログインが必要です」の「ログイン」だけをリンクにする
            toast.innerHTML = '<a href="/login/">ログイン</a>が必要です';
            toast.classList.add("show");
            clearTimeout(timer);
            timer = setTimeout(() => toast.classList.remove("show"), 4000);  // 4秒で自動的に消す
        });
    });
})();