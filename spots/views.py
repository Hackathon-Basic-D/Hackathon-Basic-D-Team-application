import json                          # JSONファイルを読み込むための標準ライブラリ
from pathlib import Path             # ファイルのパスを組み立てるための標準ライブラリ
from django.shortcuts import render  # テンプレートを描画して返す
from django.http import Http404      # 該当データが無いとき404を出すため

# スポットの静的データの場所（DBは使わず、同アプリ内の data/spots.json から読み込む）
# __file__＝このviews.pyのパス。resolve()で絶対パス化し、その親フォルダ配下の data/spots.json を指す
SPOTS_JSON = Path(__file__).resolve().parent / 'data' / 'spots.json'


# スポット一覧画面（ログイン不要・誰でも閲覧可）
def spot_list(request):
    # JSONを開いてPythonのリスト（辞書の配列）として読み込む
    with open(SPOTS_JSON, encoding='utf-8') as f:
        spots = json.load(f)
    # 地域フィルタのプルダウン用に、重複を除いた地域名を昇順で用意する
    regions = sorted({s['region'] for s in spots})
    # 一覧テンプレートへ、スポット一覧と地域一覧を渡して描画
    return render(request, 'spots/spot_list.html', {'spots': spots, 'regions': regions})


# スポット詳細画面（ログイン不要）
def spot_detail(request, pk):
    # 一覧と同じJSONを読み込む
    with open(SPOTS_JSON, encoding='utf-8') as f:
        spots = json.load(f)
    # URLの pk（＝スポットのid）に一致する1件を探す。無ければ None
    spot = next((s for s in spots if s.get('id') == pk), None)
    # 該当が無ければ404（存在しないIDでのアクセス対策）
    if spot is None:
        raise Http404('スポットが見つかりません')
    # 詳細テンプレートへ、該当スポットを渡して描画
    return render(request, 'spots/spot_detail.html', {'spot': spot})