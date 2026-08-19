// ルート詳細画面：地図にルートの地点（マーカー）を表示する
// 座標はテンプレートの data 属性（.route-point）から受け取る。経路線は次工程で追加。
const MAP_ID = "ea195c40733b8f571251ff61";        // 他画面と同じ地図ID（AdvancedMarker必須）
const PIN_IMAGE_URL = "/static/image/fire-v.png"; // ピン画像

// data属性からルートの地点を順番どおり読み取る
const points = Array.from(document.querySelectorAll(".route-point")).map((el) => ({
    lat: parseFloat(el.dataset.lat),
    lng: parseFloat(el.dataset.lng),
    title: el.dataset.title,
    order: el.dataset.order,
}));

async function initRouteMap() {
    const mapEl = document.getElementById("route-map");
    if (!mapEl || points.length === 0) return;   // 地図要素や地点が無ければ何もしない

    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    const map = new Map(mapEl, {
        center: { lat: points[0].lat, lng: points[0].lng },
        zoom: 14,
        mapId: MAP_ID,
        streetViewControl: false,
        mapTypeControl: false,
        fullscreenControl: false,
    });

    // 全地点にマーカーを立て、表示範囲を全地点が入るよう調整
    const bounds = new google.maps.LatLngBounds();
        points.forEach((p, i) => {
        // 炎画像＋順番の数字バッジを重ねたマーカー内容を作る
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
        badge.textContent = i + 1;              // 順番（1始まり。一覧の番号と一致）
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

        new AdvancedMarkerElement({ map, position: { lat: p.lat, lng: p.lng }, title: p.title, content });
        bounds.extend({ lat: p.lat, lng: p.lng });
    });
    map.fitBounds(bounds);

    // 経路線（サーバーが Routes API で計算した徒歩ルート）を取得して描画
    const pk = mapEl.dataset.routePk;
    if (pk) {
        try {
            const res = await fetch(`/routes/${pk}/polyline/`);
            const data = await res.json();
            if (data.error) console.error("経路線エラー:", data.error);   // 失敗時はコンソールにも出す
            if (data.polyline) {
                // エンコードされたポリラインを座標列に復元して線を描く
                const { encoding } = await google.maps.importLibrary("geometry");
                const path = encoding.decodePath(data.polyline);
                new google.maps.Polyline({
                    path, map, strokeColor: "#800080", strokeOpacity: 0.9, strokeWeight: 5,
                });

                // 距離・時間・注意書きを表示
                const info = document.getElementById("route-info");
                if (info) {
                    info.innerHTML = "";
                    const parts = [];
                    if (data.distance_meters != null) parts.push((data.distance_meters / 1000).toFixed(1) + "km");
                    if (data.duration_seconds != null) parts.push("約" + Math.round(data.duration_seconds / 60) + "分");
                    const summary = document.createElement("p");
                    summary.textContent = "徒歩ルート" + (parts.length ? "：" + parts.join(" / ") : "");
                    info.appendChild(summary);

                    const caution = document.createElement("p");
                    caution.textContent = "※ 徒歩ルートは歩道や歩行者用通路が反映されていない場合があります。実際の道路状況に十分ご注意ください。選択された地点の位置によっては、ルートが正確に表示されない場合があります。";
                    caution.style.fontSize = "12px";
                    info.appendChild(caution);

                    // APIから警告が返ってきていれば併せて表示
                    (data.warnings || []).forEach((w) => {
                        const p = document.createElement("p");
                        p.textContent = "※ " + w;
                        p.style.fontSize = "12px";
                        info.appendChild(p);
                    });
                }
            }
        } catch (e) {
            console.error("経路線の取得に失敗:", e);
        }
    }
}

initRouteMap();