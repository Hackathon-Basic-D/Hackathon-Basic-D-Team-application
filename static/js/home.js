// 設定関連
const PIN_IMAGE_URL = "/static/image/fire-b.png";           // 通常時のピン画像のパス
const PIN_IMAGE_SELECTED_URL = "/static/image/fire-v.png";  // クリックで選択中のときのピン画像
const MAP_ID = "c973a2f2f611aa93b5994223";                  // Google Cloudで作った地図ID（AdvancedMarker必須）
const DEFAULT_CENTER = { lat: 34.6873, lng: 135.5259 };     // 地図の初期中心（大阪城）
const PIN_SIZE = "40px";                                    // ピンの通常サイズ高さ
const PIN_SIZE_SELECTED = "64px";                           // ピンのクリック時のサイズ高さ

// 仮のスポットデータ（あとでDBに差し替え）。実際の大阪城・駅とは少しずらしています。
// ピンを立てる場所の一覧（配列）
const spots = [
    { title: "堀の近くスポット",   description: "大阪城の堀付近（仮）",   lat: 34.68585, lng: 135.52360 },
    { title: "大阪城公園駅の近く", description: "大阪城公園駅の付近（仮）", lat: 34.69080, lng: 135.53020 },
    { title: "森ノ宮駅の近く",     description: "森ノ宮駅の付近（仮）",   lat: 34.68180, lng: 135.53050 },
    { title: "スポットA",         description: "サンプル（仮）",         lat: 34.68700, lng: 135.52850 },
    { title: "スポットB",         description: "サンプル（仮）",         lat: 34.68450, lng: 135.52700 },
];

// 地図の初期化（公式推奨の importLibrary を使う）
let map;                            // 地図オブジェクトを入れる箱（後で複数の関数から使う）
let infoWindow;                     // 吹き出し(InfoWindow)を入れる箱。1個を使い回す
let displayMode = "infowindow";     // 今の表示モード。"infowindow" か "bottomsheet"
let selectedMarker = null;          // 今“選択中”のピンを覚えておく（画像切替用）。最初は無し
let currentLocationMarker = null;   // 現在地マーカーを覚えておく（2回目以降は位置だけ更新）

 // ページ表示時に一度だけ動く「準備」関数
async function initMap() {
    // "maps" ライブラリ、"AdvancedMarkerElement"ライブラリを実行時に読み込む
    const { Map, InfoWindow } = await google.maps.importLibrary("maps");            // 地図と吹き出しの部品を取り出す
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");    // 高度なマーカーの部品を取り出す

    // id="map"の要素に地図を作る
    map = new Map(document.getElementById("map"), {
        center: DEFAULT_CENTER,     // 初期の中心座標（大阪城）
        zoom: 14,                   // 初期ズーム値（数字が大きいほど拡大）
        mapId: MAP_ID,              // 地図ID（AdvancedMarkerElementを使うのに必須）
        streetViewControl: false,   // 右下の人マーク（ペグマン）を非表示
        zoomControl: false,         // ＋/− ズームボタンを非表示
        fullscreenControl: false,   // 全画面ボタンを非表示
        mapTypeControl: false,      // 地図/航空写真の切替を非表示
    });

    // infoWindowの作成
    infoWindow = new InfoWindow();                               // 吹き出しを1つ用意（使い回す）
    infoWindow.addListener("closeclick", clearSelectedMarker);  // 吹き出しの×で閉じたら、ピン画像を元に戻す

    // マーカー作成（mapは付けず、クラスタラーに任せる）
    // spots配列の1件ずつからマーカーを作り、markers配列にまとめる
    const markers = spots.map((spot) => {
        // 各マーカーごとに独立した画像要素を作る
        const img = document.createElement("img");  // ピン用の<img>を新規作成（マーカーごとに別々に必要）
        img.src = PIN_IMAGE_URL;                    // 画像の中身を通常ピンに設定
        img.style.width = "auto";                   // 表示幅
        img.style.height = PIN_SIZE;                // 表示高さ
        img.style.transition = "height 0.15s ease"  // 滑らかに変化させる
        
        // マーカー本体を作る
        const marker = new AdvancedMarkerElement({
            position: { lat: spot.lat, lng: spot.lng }, // 立てる座標
            title: spot.title,                          // マウスを乗せると出る名前（ツールチップ）
            content: img,                               // 自作画像をピンにする
            gmpClickable: true,                         // クリック可能にする（必須）
        });

        // クリックされたらshowSpotを呼ぶ
        marker.addEventListener("gmp-click", () => showSpot(spot, marker));
        return marker;  // 作ったマーカーを返す（markers配列に入る）
    });

    // クラスタ表示
    new markerClusterer.MarkerClusterer({ map, markers });  // 近いピンを自動でまとめる（数字の丸）

    // 表示モード切替(ラジオ)の準備
    setupModeSwitch();

    // 現在位置ボタンの準備（部品を渡す）
    setupLocateButton(AdvancedMarkerElement);

    // 閉じるボタンにクリック動作を付ける
    document.getElementById("bs-close").addEventListener("click", () => {
        closeBottomSheet();     // ボトムシートを閉じ
        clearSelectedMarker();  // 選択中ピンの画像も元に戻す
    });
}

// クリック時、モードに応じて表示
// ピンをクリックしたときに呼ばれる
function showSpot(spot, marker) {
    // ピン画像を切り替え
    selectMarker(marker);               // クリックしたピンを選択画像に切り替える
    // InfoWindowモードなら
    if (displayMode === "infowindow") {
        closeBottomSheet();     // ボトムシートは閉じておく
        // 吹き出しの中身を作る
        infoWindow.setContent(`<strong>${spot.title}</strong><br>${spot.description}`);
        // そのピンに吹き出しを開く
        infoWindow.open({ anchor: marker, map });
    } else {    // ボトムシートモードなら
        infoWindow.close();     // 吹き出しは閉じておく
        openBottomSheet(spot);  // ボトムシートを開く
    }
}
// クリックされたピンを選択画像に、前のピンは通常画像へ戻す
function selectMarker(marker) {
    // 別のピンが選択中だったら
    if (selectedMarker && selectedMarker !== marker) {
        selectedMarker.content.src = PIN_IMAGE_URL;             // その前のピンを通常画像へ戻す
        selectedMarker.content.style.height = PIN_SIZE;         // 前のピンを元サイズへ
    }
    marker.content.src = PIN_IMAGE_SELECTED_URL;                // 今クリックしたピンを選択画像に
    marker.content.style.height = PIN_SIZE_SELECTED;    // 選択中のピンを拡大
    selectedMarker = marker;                                    // 「選択中ピン」を更新
}
// 選択解除（閉じたとき用）
function clearSelectedMarker() {
    // 選択中のピンがあれば
    if (selectedMarker) {
        selectedMarker.content.src = PIN_IMAGE_URL;     // 通常画像へ戻し
        selectedMarker.content.style.height = PIN_SIZE; // 元サイズへ戻す
        selectedMarker = null;                          // 選択なしにする
    }
}

// ボトムシート
// ボトムシートを開いて内容を入れる
function openBottomSheet(spot) {
    document.getElementById("bs-title").textContent = spot.title;       // タイトル欄に名前を入れる
    document.getElementById("bs-desc").textContent = spot.description;  // 説明欄に説明を入れる
    document.getElementById("bottom-sheet").classList.add("open");      // openクラスを付けてせり上げる
}
// ボトムシートを閉じる
function closeBottomSheet() {
    document.getElementById("bottom-sheet").classList.remove("open");   // openクラスを外して隠す
}

// モード切替（切り替えたら開いているものを閉じる）
function setupModeSwitch() {
    document.querySelectorAll('input[name="display-mode"]').forEach((r) => {
        // 選択が変わったとき
        r.addEventListener("change", (e) => {
            displayMode = e.target.value;   // 今のモードを更新（infowindow/bottomsheet）
            infoWindow.close();             // 開いていた吹き出しを閉じる
            closeBottomSheet();             // 開いていたシートを閉じる
            clearSelectedMarker();          // ピン画像を元に戻す
        });
    });
}

// 現在地ボタン：位置情報を取得して地図を移動し、現在地マーカーを置く
// 部品(AdvancedMarkerElement)を受け取る
function setupLocateButton(AdvancedMarkerElement) {
    const btn = document.getElementById("locate-btn");      // 現在地ボタンを取得

    // ボタンが押されたら
    btn.addEventListener("click", () => {
        // この端末が位置情報に対応していなければ
        if (!navigator.geolocation) {
            alert("この端末では現在地を取得できません。");  // 処理を中断
        return;
    }
    // 取得中は二度押し防止でボタンを無効化
    btn.disabled = true;

    // 現在地の取得を開始（許可ダイアログが出る）
    navigator.geolocation.getCurrentPosition(
        // 【成功時】posに位置が入る
        (pos) => {
            btn.disabled = false;       // ボタンを再び有効化
            const here = { lat: pos.coords.latitude, lng: pos.coords.longitude };   // 取得した緯度経度

            map.setCenter(here);        // 地図の中心を現在地へ
            map.setZoom(16);            // 少し拡大

            // 現在地マーカーを置く（2回目以降は位置だけ更新）
            if (!currentLocationMarker) {
                // まだ現在地マーカーが無ければ新規作成
                const dot = document.createElement("div");  // 青い丸用のdivを作る
                dot.className = "current-dot";              // CSSの.current-dotを適用

                // マーカーとして地図に追加
                currentLocationMarker = new AdvancedMarkerElement({
                    map,                // 表示先の地図
                    position: here,     // 現在地の座標
                    title: "現在地",    // ツールチップ
                    content: dot,       // 中身は青い丸
                });
            } else {    // すでにあれば
                currentLocationMarker.position = here;  // 位置だけ更新（作り直さない）
            }
        },
        // 【失敗時】errに理由が入る
        (err) => {
            btn.disabled = false;       // ボタンを有効化
            // 許可が拒否された場合
            if (err.code === err.PERMISSION_DENIED) {
                alert("位置情報の利用が許可されていません。ブラウザの設定で許可してください。");
            } else {    // それ以外(取得失敗・時間切れ等)
                alert("現在地を取得できませんでした。");
            }
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 } // 取得の設定：高精度・10秒で時間切れ・キャッシュ不可
        );
    });
}

// 最後に初期化を実行してページを立ち上げる
initMap();