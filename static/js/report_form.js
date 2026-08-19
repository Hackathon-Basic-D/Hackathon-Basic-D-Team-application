// レポート作成画面：URL の lat/lng を読み取り、確認用の静的地図（画像）を表示する
const MAP_ID = "ea195c40733b8f571251ff61";   // 動的地図(home.js)と同じ Map ID。クラウド側のスタイルを適用する

(function () {
    // 静的地図を表示する<img>要素を取得
    const img = document.getElementById("report-static-map");
    if (!img) return;   // 対象要素が無ければ何もしない（他ページで誤って読み込まれた場合の保険）

    // URLのクエリ文字列（?lat=..&lng=..）を解析する
    const params = new URLSearchParams(location.search);
    const lat = params.get("lat");   // 緯度を取り出す
    const lng = params.get("lng");   // 経度を取り出す
    if (!lat || !lng) return;        // 座標が無ければ地図は出さない（位置未指定でのアクセス対策）

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

// 入力中はフッターを隠す（ソフトキーボードと重なって入力欄が隠れるのを防ぐ）
