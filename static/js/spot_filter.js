// スポット一覧：検索文字＋地域で、表示中の行をクライアント側で絞り込む
(function () {
    const input = document.getElementById("spot-search");
    const region = document.getElementById("spot-region");
    const list = document.getElementById("spot-list");
    if (!list) return;

    const rows = Array.from(list.querySelectorAll(".spot-row"));
    if (!rows.length) return;   // データが無いときはテンプレート側の表示に任せる

    // 「該当なし」メッセージ（絞り込み結果が0件のとき表示）
    const empty = document.createElement("p");
    empty.className = "feed-empty";
    empty.textContent = "該当するスポットがありません。";
    empty.style.display = "none";
    list.appendChild(empty);

    // 現在の検索文字・地域で行の表示/非表示を切り替える
    function apply() {
        const q = (input && input.value ? input.value : "").trim().toLowerCase();
        const r = region ? region.value : "";
        let shown = 0;
        rows.forEach((row) => {
            // タイトル・説明・タグ・地域をまとめて検索対象にする
            const hay = (
                (row.dataset.title || "") + " " +
                (row.dataset.description || "") + " " +
                (row.dataset.tags || "") + " " +
                (row.dataset.region || "")
            ).toLowerCase();
            const matchText = q === "" || hay.indexOf(q) !== -1;
            const matchRegion = r === "" || row.dataset.region === r;
            const show = matchText && matchRegion;
            row.style.display = show ? "" : "none";
            if (show) shown++;
        });
        empty.style.display = shown === 0 ? "" : "none";
    }

    if (input) input.addEventListener("input", apply);     // 入力中に絞り込み
    if (region) region.addEventListener("change", apply);  // 地域を変えたとき
    const btn = document.getElementById("spot-search-btn");
    if (btn) btn.addEventListener("click", apply);          // 検索ボタンでも

    apply();   // 初期表示
})();