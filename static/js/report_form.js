// レポート作成画面：URL の lat/lng を読み取り、確認用の静的地図（画像）を表示する
const MAP_ID = "ea195c40733b8f571251ff61";   // 動的地図(home.js)と同じ Map ID。クラウド側のスタイルを適用する

(function () {
    // 静的地図を表示する<img>要素を取得
    const img = document.getElementById("report-static-map");
    if (!img) return;   // 対象要素が無ければ何もしない（他ページで誤って読み込まれた場合の保険）

    // 座標を取得：作成時はURLの ?lat=&lng= から、編集時はフォームのhidden（既存レポートの座標）から
    const params = new URLSearchParams(location.search);
    const latEl = document.querySelector('[name="latitude"]');   // hidden（編集時に既存の緯度が入っている）
    const lngEl = document.querySelector('[name="longitude"]');   // hidden（同・経度）
    const lat = params.get("lat") || (latEl ? latEl.value : "");  // URL優先、無ければhidden
    const lng = params.get("lng") || (lngEl ? lngEl.value : "");
    if (!lat || !lng) return;   // どちらにも無ければ地図は出さない

    // 地図APIキーをHTMLの data-map-key 属性から受け取る
    const key = img.dataset.mapKey;

    // Maps Static API の画像URLを組み立てて <img> の src に設定する
    // マーカーは付けない（選択地点はHTML/CSSで中央に「＋」を重ねて示す）
    img.src =
        "https://maps.googleapis.com/maps/api/staticmap"   // 静的地図APIのエンドポイント
        + `?center=${lat},${lng}`                          // 地図の中心＝選択した座標（＝画像の中央）
        + "&zoom=16&size=600x300&scale=2"                  // ズーム・画像サイズ・高解像度(2倍表示)
        + `&map_id=${MAP_ID}`                              // 動的地図と同じ Map ID でスタイルを揃える
        + `&key=${key}`;                                   // APIキー
})();

// 画像プレビュー：選択した画像を送信前に表示する（編集時は既存画像が初期表示されている）
(function () {
    const fileInput = document.querySelector('[name="report_image"]');  // 画像のファイル入力
    const preview = document.getElementById("report-image-preview");     // プレビュー用の<img>
    if (!fileInput || !preview) return;                    // どちらか無ければ何もしない
    fileInput.addEventListener("change", () => {           // ファイルが選ばれたら
        const file = fileInput.files && fileInput.files[0]; // 選択された最初の1枚を取り出す
        if (!file) return;                                  // 未選択なら何もしない
        preview.src = URL.createObjectURL(file);            // 選んだ画像をその場でプレビュー表示
        preview.hidden = false;                             // 隠していたら表示する
    });
})();