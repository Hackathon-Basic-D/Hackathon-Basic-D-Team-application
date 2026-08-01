// 地図の初期化（公式推奨の importLibrary を使う）
let map;

async function initMap() {
  // "maps" ライブラリを実行時に読み込む
  const { Map } = await google.maps.importLibrary("maps");

  map = new Map(document.getElementById("map"), {
    center: { lat: 35.681236, lng: 139.767125 }, // 東京駅
    zoom: 14,  // 初期ズーム値
    mapId: "c973a2f2f611aa93b5994223",  // 自分の作ったMapID
    streetViewControl: false,   // 右下の人マーク（ペグマン）
    zoomControl: true,         // ＋/− ズーム
    fullscreenControl: false,   // 全画面ボタン
    mapTypeControl: false,     // 地図/航空写真の切替（不要ならfalse）
  });
}

initMap();