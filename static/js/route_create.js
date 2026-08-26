// 作成画面：選択した投稿の順番を「↑／↓」ボタンで並び替える
// 並び替えた順番を、保存フォーム内の hidden input (report_ids) に反映する
(function () {
    const list = document.getElementById("reorder-list");
    const container = document.getElementById("route-ids-container");
    if (!list || !container) return;   // 対象要素が無ければ何もしない

    // 現在のリスト順で、番号の振り直しと hidden input の作り直しを行う
    function sync() {
        const items = Array.from(list.querySelectorAll(".reorder-item"));
        container.innerHTML = "";
        items.forEach((li, i) => {
            // 表示の順番番号（1始まり）
            const idx = li.querySelector(".reorder-index");
            if (idx) idx.textContent = (i + 1) + ".";
            // 先頭は「↑」、末尾は「↓」を押せなくする
            const up = li.querySelector(".reorder-up");
            const down = li.querySelector(".reorder-down");
            if (up) up.disabled = (i === 0);
            if (down) down.disabled = (i === items.length - 1);
            // 保存フォームに送る hidden input を順番どおりに作る
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "report_ids";
            input.value = li.dataset.reportId;
            container.appendChild(input);
        });
    }

    // クリックされた行を1つ上／下へ動かす
    list.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        const li = btn.closest(".reorder-item");
        if (!li) return;
        if (btn.classList.contains("reorder-up")) {
            const prev = li.previousElementSibling;
            if (prev) list.insertBefore(li, prev);        // 前の行と入れ替え
        } else if (btn.classList.contains("reorder-down")) {
            const next = li.nextElementSibling;
            if (next) list.insertBefore(next, li);        // 次の行と入れ替え
        }
        sync();
    });

    sync();   // 初期表示：番号付け＋hidden input 生成
})();


// ===== 「この順番でルートを確定」→ 徒歩ルートをプレビュー表示 =====
(function () {
    const MAP_ID = "ea195c40733b8f571251ff61";        // 他画面と同じ地図ID
    const PIN_IMAGE_URL = "/static/image/fire-v.png"; // ピン画像

    const btn = document.getElementById("route-confirm-btn");
    const mapEl = document.getElementById("route-preview-map");
    const infoEl = document.getElementById("route-preview-info");
    const list = document.getElementById("reorder-list");
    if (!btn || !mapEl || !list) return;

    let map = null;
    let markers = [];
    let polyline = null;

    // いまの並び順で地点（id, lat, lng, title）を集める
    function collectPoints() {
        return Array.from(list.querySelectorAll(".reorder-item")).map((li) => ({
            id: li.dataset.reportId,
            lat: parseFloat(li.dataset.lat),
            lng: parseFloat(li.dataset.lng),
            title: (li.querySelector(".reorder-title") || {}).textContent || "",
        }));
    }

    // 前回のマーカー・線を消す
    function clearOverlays() {
        markers.forEach((m) => (m.map = null));
        markers = [];
        if (polyline) { polyline.setMap(null); polyline = null; }
    }

    // CSRFトークンを保存フォームから取得
    function csrfToken() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : "";
    }

    btn.addEventListener("click", async () => {
        const points = collectPoints();
        if (points.length < 2) {
            if (infoEl) infoEl.textContent = "ルートには2件以上必要です。";
            return;
        }

        mapEl.style.display = "block";   // 初期化前に地図へサイズを持たせる

        const { Map } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

        if (!map) {
            map = new Map(mapEl, {
                center: { lat: points[0].lat, lng: points[0].lng },
                zoom: 14,
                mapId: MAP_ID,
                streetViewControl: false,
                mapTypeControl: false,
                fullscreenControl: false,
            });
        }

        clearOverlays();

        // 番号付きマーカーを置き、全地点が入るよう表示範囲を調整
        const bounds = new google.maps.LatLngBounds();
        points.forEach((p, i) => {
            const content = document.createElement("div");
            content.style.position = "relative";
            content.style.width = "40px";
            content.style.height = "40px";

            const img = document.createElement("img");
            img.src = PIN_IMAGE_URL;
            img.style.height = "40px";
            img.style.width = "auto";
            content.appendChild(img);

            const badge = document.createElement("span");
            badge.textContent = i + 1;
            badge.style.position = "absolute";
            badge.style.top = "-6px";
            badge.style.right = "-6px";
            badge.style.width = "18px";
            badge.style.height = "18px";
            badge.style.borderRadius = "50%";
            badge.style.background = "#800080";
            badge.style.color = "#fff";
            badge.style.fontSize = "12px";
            badge.style.lineHeight = "18px";
            badge.style.textAlign = "center";
            content.appendChild(badge);

            const marker = new AdvancedMarkerElement({ map, position: { lat: p.lat, lng: p.lng }, title: p.title, content });
            markers.push(marker);
            bounds.extend({ lat: p.lat, lng: p.lng });
        });
        map.fitBounds(bounds);

        // 徒歩ルートをサーバーで計算（保存前なので report_ids を送る）
        if (infoEl) infoEl.textContent = "ルートを計算しています…";
        try {
            const params = new URLSearchParams();
            params.append("csrfmiddlewaretoken", csrfToken());
            points.forEach((p) => params.append("report_ids", p.id));
            const res = await fetch("/routes/create/preview/", { method: "POST", body: params });
            const data = await res.json();
            if (data.error) console.error("プレビュー経路エラー:", data.error);

            if (data.polyline) {
                const { encoding } = await google.maps.importLibrary("geometry");
                const path = encoding.decodePath(data.polyline);
                polyline = new google.maps.Polyline({
                    path, map, strokeColor: "#800080", strokeOpacity: 0.9, strokeWeight: 5,
                });
            }

            // 距離・時間・注意書きを表示（詳細画面と同じ内容）
            if (infoEl) {
                infoEl.innerHTML = "";
                const parts = [];
                if (data.distance_meters != null) parts.push((data.distance_meters / 1000).toFixed(1) + "km");
                if (data.duration_seconds != null) parts.push("約" + Math.round(data.duration_seconds / 60) + "分");
                const summary = document.createElement("p");
                summary.textContent = "徒歩ルート" + (parts.length ? "：" + parts.join(" / ") : "");
                infoEl.appendChild(summary);

                                // 注意書き（文ごとに改行。詳細画面と同じ .route-caution） 
                const cautionLines = [
                    "※ 徒歩ルートは歩道や歩行者用通路が反映されていない場合があります。",
                    "※ 実際の道路状況に十分ご注意ください。",
                    "※ 選択された地点の位置によっては、ルートが正確に表示されない場合があります。",
                ];
                cautionLines.forEach((text) => {
                    const c = document.createElement("p");
                    c.textContent = text;
                    c.className = "route-caution";
                    infoEl.appendChild(c);
                });

                (data.warnings || []).forEach((w) => {
                    const p = document.createElement("p");
                    p.textContent = "※ " + w;
                    p.className = "route-caution";
                    infoEl.appendChild(p);
                });
            }
        } catch (e) {
            console.error("プレビューの取得に失敗:", e);
            if (infoEl) infoEl.textContent = "ルートの取得に失敗しました。";
        }
    });
})();