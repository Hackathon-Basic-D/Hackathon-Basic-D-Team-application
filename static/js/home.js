// 設定関連
const PIN_IMAGE_URL = "/static/image/fire-v.png";           // 通常時のピン画像のパス
const PIN_IMAGE_SELECTED_URL = "/static/image/fire-v.png";  // クリックで選択中のときのピン画像
const MAP_ID = "ea195c40733b8f571251ff61";                  // Google Cloudで作った地図ID（AdvancedMarker必須）
const DEFAULT_CENTER = { lat: 34.6873, lng: 135.5259 };     // 地図の初期中心（大阪城）
const PIN_SIZE = "40px";                                    // ピンの通常サイズ高さ
const PIN_SIZE_SELECTED = "64px";                           // ピンのクリック時のサイズ高さ

let reportMode = false;                                     // レポートモードの状態（true の間は既存ピンの選択を無効化）


// 仮のスポットデータ（デモ表示用。idはDBのpkと絶対に被らないよう大きな値にしてある）
const mockSpots = [
    { id: 1000001, title: "堀の近くスポット",   date: "2026年7月28日 14:30", description: "大阪城の堀付近（仮）",   lat: 34.68585, lng: 135.52360 },
    { id: 1000002, title: "大阪城公園駅の近く", date: "2026年7月27日 21:30", description: "大阪城公園駅の付近（仮）", lat: 34.69080, lng: 135.53020 },
    { id: 1000003, title: "森ノ宮駅の近く",     date: "2026年7月26日 10:00", description: "森ノ宮駅の付近（仮）",   lat: 34.68180, lng: 135.53050 },
    { id: 1000004, title: "スポットA",         date: "2026年7月25日 09:15", description: "サンプル（仮）",         lat: 34.68700, lng: 135.52850 },
    { id: 1000005, title: "スポットB",         date: "2026年7月24日 18:45", description: "サンプル（仮）",         lat: 34.68450, lng: 135.52700 },
];

// ピンを立てる場所の一覧（配列）。DB連携(window.REPORTS_DATA)はそのまま使い、
// デモ表示用に仮データ5件も合わせて表示する
const spots = [...(window.REPORTS_DATA || []), ...mockSpots];

// 地図の初期化（公式推奨の importLibrary を使う）
let map;                            // 地図オブジェクトを入れる箱（後で複数の関数から使う）
let selectedMarker = null;          // 今“選択中”のピンを覚えておく（画像切替用）。最初は無し
let currentLocationMarker = null;   // 現在地マーカーを覚えておく（2回目以降は位置だけ更新）

 // ページ表示時に一度だけ動く「準備」関数
async function initMap() {
    // "maps" ライブラリ、"AdvancedMarkerElement"ライブラリを実行時に読み込む
    const { Map } = await google.maps.importLibrary("maps");            // 地図と吹き出しの部品を取り出す
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

    // 報告モード中、地図上のクリックした地点をレポート作成画面へ引き継ぐ
    map.addListener("click", (e) => {
        if (!reportMode) return;   // 通常モード中は何もしない
        const lat = e.latLng.lat();
        const lng = e.latLng.lng();
        window.location.href = `/reports/create/?lat=${lat}&lng=${lng}`;
    });

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
    if (reportMode) return;   // 報告モード中は既存ピンのタップを無効化
    // レポート詳細画面へ直接遷移
    window.location.href = `/reports/${spot.id}/`;
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
    document.getElementById("bs-title").textContent = spot.title;       // タイトル
    // document.getElementById("bs-detail").href = `/reports/${spot.id}/`;            // タイトル横「詳細を見る」
    document.getElementById("bs-date").textContent = spot.date;         // 投稿日時（有効化）

    // 本文：載せると決めたら次の行を有効化（今は枠だけ）
    // document.getElementById("bs-desc").textContent = spot.description;

    document.getElementById("bs-nav").href = googleMapsDirUrl(spot);     // Googleマップ
    document.getElementById("bottom-sheet").classList.add("open");       // せり上げて表示
    document.getElementById("map").classList.add("sheet-open");         // 地図をシート高さぶん縮める → ロゴ・規約がシートの上に出て隠れない
    map.setCenter({ lat: spot.lat, lng: spot.lng });                    // 縮んだ表示領域の中央に選択ピンを置く
}
// ボトムシートを閉じる
function closeBottomSheet() {
    document.getElementById("bottom-sheet").classList.remove("open");   // openクラスを外して隠す
    document.getElementById("map").classList.remove("sheet-open");    // 地図の高さを元に戻す
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

// そのスポットへの徒歩ルートをGoogleマップで開くURLを作る
function googleMapsDirUrl(spot) {
    return `https://www.google.com/maps/dir/?api=1&destination=${spot.lat},${spot.lng}&travelmode=walking`;
}

// フッターのレポートボタンを横取りして、遷移せず報告モードに入る（ホームでだけ動く）
const reportBtn = document.querySelector('.footer-menu a[href*="reports/create"]');
if (reportBtn) {
    reportBtn.addEventListener("click", (e) => {
        e.preventDefault();     // 作成画面へは遷移しない
        enterReportMode();
    });
}

// 報告モードに入る
function enterReportMode() {
    reportMode = true;
    document.getElementById("report-message").classList.add("show"); // 案内を表示
    closeBottomSheet();     // 開いていれば閉じる
    clearSelectedMarker();  // 選択中ピンを元に戻す
}

// フッターのホームボタン：ホームに居るときは再読み込みせず、表示を通常状態に戻す
const homeBtn = document.querySelector('.footer-menu img[alt="ホーム"]')?.closest("a");
if (homeBtn) {
    homeBtn.addEventListener("click", (e) => {
        e.preventDefault();     // 再読み込み（マップロード）をしない
        resetHome();
    });
}

// ホーム表示を通常状態に戻す（報告モード解除・シート閉じ）
function resetHome() {
    reportMode = false;
    document.getElementById("report-message").classList.remove("show"); // 案内を消す
    closeBottomSheet();     // シートを閉じる
    clearSelectedMarker();  // 選択中ピンを戻す
}

// 最後に初期化を実行してページを立ち上げる
initMap();
