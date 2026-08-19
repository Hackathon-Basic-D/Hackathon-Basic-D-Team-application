// ルート用レポート選択画面のJS

// ===== 設定（home と同じ値）=====
const PIN_IMAGE_URL = "/static/image/fire-v.png";        // ピン画像
const MAP_ID = "ea195c40733b8f571251ff61";               // 地図ID（AdvancedMarker必須）
const DEFAULT_CENTER = { lat: 34.6873, lng: 135.5259 };  // 初期中心（大阪城）
const PIN_SIZE = "40px";           // 通常時のピン高さ
const PIN_SIZE_SELECTED = "64px";  // タップ時のピン高さ

// ===== 段階1用ダミーデータ（直書き。段階2で実データへ差し替え）=====
// const spots = [
//     { id: 1000001, title: "堀の近くスポット",   date: "2026年7月28日 14:30", description: "大阪城の堀付近（仮）",   lat: 34.68585, lng: 135.52360, description:"テストテストテストテストテストテストテストテストテストテストテストテストテストテストテスト"},
//     { id: 1000002, title: "大阪城公園駅の近く", date: "2026年7月27日 21:30", description: "大阪城公園駅の付近（仮）", lat: 34.69080, lng: 135.53020 , description:"テスト"},
//     { id: 1000003, title: "森ノ宮駅の近く",     date: "2026年7月26日 10:00", description: "森ノ宮駅の付近（仮）",   lat: 34.68180, lng: 135.53050 , description:"テスト"},
//     { id: 1000004, title: "スポットA",          date: "2026年7月25日 09:15", description: "サンプル（仮）",          lat: 34.68700, lng: 135.52850 , description:"テスト"},
//     { id: 1000005, title: "スポットB",          date: "2026年7月24日 18:45", description: "サンプル（仮）",          lat: 34.68450, lng: 135.52700 , description:"テスト"},
//     { id: 1000006, title: "スポットC", date: "2026年7月23日 12:00", description: "サンプル（仮）", lat: 34.69300, lng: 135.52000 },
//     { id: 1000007, title: "スポットD", date: "2026年7月22日 15:20", description: "サンプル（仮）", lat: 34.68000, lng: 135.51500 },
//     { id: 1000008, title: "スポットE", date: "2026年7月21日 08:40", description: "サンプル（仮）", lat: 34.69500, lng: 135.53500 },
//     { id: 1000009, title: "スポットF", date: "2026年7月20日 19:10", description: "サンプル（仮）", lat: 34.67800, lng: 135.53500 },
//     { id: 1000010, title: "スポットG", date: "2026年7月19日 11:05", description: "サンプル（仮）", lat: 34.69100, lng: 135.51200 },
//     { id: 1000011, title: "スポットH", date: "2026年7月18日 16:30", description: "サンプル（仮）", lat: 34.67600, lng: 135.52200 },
//     { id: 1000012, title: "スポットI", date: "2026年7月17日 07:50", description: "サンプル（仮）", lat: 34.69700, lng: 135.52600 },
// ];
const spots = window.REPORTS_DATA || [];

// ===== この画面で選んだスポットの状態 =====
const MAX_SPOTS = 9;      // 最大9件
const MIN_SPOTS = 2;      // 最小2件（送信時にチェック）
const selectedIds = [];   // 選んだレポートIDをタップ順で保持
const markerById = {};    // id からマーカーを引く（選択印の付け外し用）
let currentSpot = null;   // いまボトムシートで開いているスポット
let alertTimer = null;   // 警告の自動非表示タイマー

let map;                    // 地図オブジェクト
let AdvancedMarker = null;  // マーカー部品を保持（現在地ボタンでも使う）
let selectedMarker = null;  // いまボトムシートで開いているピン（画像切替用）

// 地図の初期化（home と同じ手順）
async function initMap() {
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
    AdvancedMarker = AdvancedMarkerElement;

    map = new Map(document.getElementById("map"), {
        center: DEFAULT_CENTER,
        zoom: 14,
        mapId: MAP_ID,
        streetViewControl: false,
        zoomControl: false,
        fullscreenControl: false,
        mapTypeControl: false,
    });
    // 選択画面では案内を常に表示する
    document.getElementById("report-message").classList.add("show");

    // ダミー各スポットからマーカーを作る（home と同じ作り方）
    const markers = spots.map((spot) => {
        const markerContent = document.createElement("div");
        markerContent.className = "fire-marker";
        const pulse = document.createElement("span");
        pulse.className = "fire-pulse";
        const img = document.createElement("img");
        img.className = "fire-marker-image";
        img.src = PIN_IMAGE_URL;
        img.style.width = "auto";
        img.style.height = PIN_SIZE;
        img.style.transition = "height 0.15s ease";
        markerContent.appendChild(pulse);
        markerContent.appendChild(img);

        const marker = new AdvancedMarkerElement({
            position: { lat: spot.lat, lng: spot.lng },
            title: spot.title,
            content: markerContent,
            gmpClickable: true,
        });
        markerById[spot.id] = marker;   // 後で選択印を付け外しするため保持
        // タップでボトムシートを開く
        marker.addEventListener("gmp-click", () => showSpot(spot, marker));
        return marker;
    });

    // 近いピンをまとめる（home と同じクラスタリング）
    new markerClusterer.MarkerClusterer({ map, markers });

    // 現在地ボタン
    setupLocateButton(AdvancedMarker);

    // ボトムシートの閉じるボタン
    document.getElementById("bs-close").addEventListener("click", () => {
        closeBottomSheet();
        clearSelectedMarker();
    });
    // ボトムシートの「ルートに追加／外す」
    document.getElementById("bs-add").addEventListener("click", toggleAdd);
    updateCount();   // 初期件数（0）を表示

    // 「選択した投稿でルート作成する」の送信
    document.getElementById("route-next-form").addEventListener("submit", onSubmitRoute);
}

// タップ時：ピン画像を切替＋ボトムシート表示
function showSpot(spot, marker) {
    selectMarker(marker);
    openBottomSheet(spot);
}

// タップしたピンを拡大表示、前のピンは戻す
function selectMarker(marker) {
    if (selectedMarker && selectedMarker !== marker) {
        const prev = selectedMarker.content.querySelector(".fire-marker-image");
        prev.style.height = PIN_SIZE;
        selectedMarker.content.classList.remove("burning");
    }
    const img = marker.content.querySelector(".fire-marker-image");
    img.style.height = PIN_SIZE_SELECTED;
    marker.content.classList.add("burning");
    selectedMarker = marker;
}

// 選択解除（閉じたとき）
function clearSelectedMarker() {
    if (selectedMarker) {
        const img = selectedMarker.content.querySelector(".fire-marker-image");
        img.style.height = PIN_SIZE;
        selectedMarker.content.classList.remove("burning");
        selectedMarker = null;
    }
}

// ボトムシートを開く（段階1：タイトル・本文・日時のみ表示）
function openBottomSheet(spot) {
    currentSpot = spot;   // いま開いているスポット（追加/外すの対象）を覚える
    document.getElementById("bs-title").textContent = spot.title;
    document.getElementById("bs-desc").textContent = spot.description;
    document.getElementById("bs-date").textContent = spot.date;
    updateAddButton();    // ボタン表示を選択状態に合わせる（追加 or 外す）
    document.getElementById("bottom-sheet").classList.add("open");
    document.getElementById("map").classList.add("sheet-open");
    map.setCenter({ lat: spot.lat, lng: spot.lng });
}

// ボトムシートのボタン表示を選択状態に合わせる
function updateAddButton() {
    const btn = document.getElementById("bs-add");
    if (!btn || !currentSpot) return;
    const added = selectedIds.includes(currentSpot.id);
    btn.textContent = added ? "ルートから外す" : "ルートに追加";  // 状態で文言を切替
}

// 「ルートに追加／外す」ボタンが押されたとき
function toggleAdd() {
    if (!currentSpot) return;
    const id = currentSpot.id;
    const idx = selectedIds.indexOf(id);
    if (idx >= 0) {
        // すでに選択済み → 外す
        selectedIds.splice(idx, 1);
        clearBadge(markerById[id]);   // 外したマーカーの番号を消す
        updateBadges();               // 残りの番号を振り直す
        updateCount();
        closeSheet();                 // 外したらシートを閉じる
    } else {
        // 未選択 → 追加（最大9件）
        if (selectedIds.length >= MAX_SPOTS) {
            showAlert("スポットは最大" + MAX_SPOTS + "件までです。");
            return;                   // 上限時はシートを閉じない
        }
        selectedIds.push(id);         // タップ順で末尾に追加
        updateBadges();               // 追加したマーカーに番号を付ける
        updateCount();
        closeSheet();                 // 追加したらシートを閉じる
    }
}

// 指定マーカーに順番の数字バッジを付ける（無ければ作る／あれば数字を更新）
function setBadge(marker, number) {
    if (!marker) return;
    let badge = marker.content.querySelector(".select-badge");
    if (!badge) {
        badge = document.createElement("span");
        badge.className = "select-badge";
        // CSSファイルを増やさないための最小インライン指定
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
        marker.content.style.position = "relative";   // バッジ配置の基準
        marker.content.appendChild(badge);
    }
    badge.textContent = number;   // 順番の数字（1始まり）
}

// マーカーからバッジを消す
function clearBadge(marker) {
    if (!marker) return;
    const badge = marker.content.querySelector(".select-badge");
    if (badge) badge.remove();
}

// 選択リストの順番どおりに、全マーカーの番号を振り直す
function updateBadges() {
    selectedIds.forEach((id, i) => setBadge(markerById[id], i + 1));
}

// 「選択した投稿でルート作成する（件数）」の件数を更新
function updateCount() {
    const el = document.getElementById("route-count");
    if (el) el.textContent = selectedIds.length;
}

// ボトムシートを閉じる
function closeBottomSheet() {
    document.getElementById("bottom-sheet").classList.remove("open");
    document.getElementById("map").classList.remove("sheet-open");
}

// 現在地ボタン（home と同じ処理）
function setupLocateButton(AdvancedMarkerElement) {
    const btn = document.getElementById("locate-btn");
    if (!btn) return;
    let currentLocationMarker = null;
    btn.addEventListener("click", () => {
        if (!navigator.geolocation) { alert("この端末では現在地を取得できません。"); return; }
        btn.disabled = true;
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                btn.disabled = false;
                const here = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                map.setCenter(here);
                map.setZoom(16);
                if (!currentLocationMarker) {
                    const dot = document.createElement("div");
                    dot.className = "current-dot";
                    currentLocationMarker = new AdvancedMarkerElement({ map, position: here, title: "現在地", content: dot });
                } else {
                    currentLocationMarker.position = here;
                }
            },
            (err) => {
                btn.disabled = false;
                if (err.code === err.PERMISSION_DENIED) alert("位置情報の利用が許可されていません。ブラウザの設定で許可してください。");
                else alert("現在地を取得できませんでした。");
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    });
}

// シートを閉じて、開いていたマーカーの拡大表示も元に戻す（×ボタンと同じ挙動）
function closeSheet() {
    closeBottomSheet();
    clearSelectedMarker();
}

// アプリ内メッセージを数秒だけ表示する（ブラウザの alert の代わり）
function showAlert(msg) {
    const el = document.getElementById("route-alert");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(alertTimer);
    alertTimer = setTimeout(() => el.classList.remove("show"), 2500);  // 2.5秒で自動的に消す
}

// 送信時：件数を検証し、選択IDを順番どおり hidden input に詰めて送る
function onSubmitRoute(e) {
    if (selectedIds.length < MIN_SPOTS) {
        e.preventDefault();                                  // 送信を止める
        showAlert(MIN_SPOTS + "件以上選んでください。");
        return;
    }
    if (selectedIds.length > MAX_SPOTS) {                     // 念のため（追加時にも制限済み）
        e.preventDefault();
        showAlert("最大" + MAX_SPOTS + "件までです。");
        return;
    }
    // 検証OK → 選択IDを report_ids として詰める（既存ビューは getlist('report_ids') で読む）
    const container = document.getElementById("route-ids-container");
    container.innerHTML = "";
    selectedIds.forEach((id) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "report_ids";
        input.value = id;
        container.appendChild(input);
    });
    // ここでは preventDefault しない＝通常どおりフォーム送信
}

// 初期化実行
initMap();

