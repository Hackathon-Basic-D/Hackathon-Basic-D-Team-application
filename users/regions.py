import json
import os
import re
from django.conf import settings

# 都道府県境界GeoJSON（static直下）。サーバー側で1回だけ読み込んでキャッシュする。
_GEOJSON_PATH = os.path.join(settings.BASE_DIR, 'static', 'japan_prefectures.geojson')
_prefectures = None  # 都道府県データのキャッシュ。_load() が初回に読み込んで格納する

def _load():
    """GeoJSONを読み込み、(都道府県名, ポリゴン群) のリストにして返す（初回のみ実読み込み）。"""
    global _prefectures
    if _prefectures is not None:
        return _prefectures
    _prefectures = []
    try:
        with open(_GEOJSON_PATH, encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return _prefectures  # ファイルが無い/壊れている時は空＝接頭辞なしで動作継続
    for feat in data.get('features', []):
        props = feat.get('properties', {})
        name = props.get('nam_ja') or props.get('nam') or ''      # 日本語名（例: 大阪府）
        geom = feat.get('geometry', {})
        gtype = geom.get('type')
        coords = geom.get('coordinates', [])
        if gtype == 'Polygon':
            polygons = [coords]        # coords = [ring, ...]
        elif gtype == 'MultiPolygon':
            polygons = coords          # coords = [polygon, ...]
        else:
            polygons = []
        _prefectures.append((name, polygons))
    return _prefectures


def _point_in_ring(lng, lat, ring):
    """ray-casting：点(lng,lat)が閉じた輪(ring)の内側かどうか。交差回数が奇数なら内側。"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]   # GeoJSONは [経度, 緯度] の順
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_polygon(lng, lat, polygon):
    """polygon = [外周, 穴1, 穴2, ...]。外周に入り、穴には入っていなければ内側。"""
    if not polygon or not _point_in_ring(lng, lat, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(lng, lat, hole):
            return False
    return True


def prefecture_of(lat, lng):
    """緯度経度→都道府県名（例 '大阪府'）。該当なし（海上・国外・不正値）は ''。"""
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return ''
    for name, polygons in _load():
        for polygon in polygons:
            if _point_in_polygon(lng, lat, polygon):
                return name
    return ''


_PREFIX_RE = re.compile(r'^\s*【[^】]*】\s*')  # 先頭の【…】

# 都道府県を判定できない座標（海上・国外・座標不正など）に付ける代替ラベル。
# タイトルを「必ず先頭に【…】が付く」形に統一するため、判定不可でも空にせずこれを付ける。
# （'不明' 等に変えたいときはここだけ直す）
UNKNOWN_REGION = 'その他'


def with_region_prefix(title, region, max_length=None):
    """タイトル先頭の既存【…】を除去してから【region】を付ける
    region が空（prefecture_of が判定できなかった場合）は UNKNOWN_REGION（【その他】）を付ける
    max_length を渡すと、【…】を付けた結果がその文字数を超えないよう本文側を末尾から切り詰める
    フォームの検証はラベルを付ける前の長さで通るため、ここで保証しないと、カラム長を超えて MySQL の Data too long で保存に失敗する"""
    base = _PREFIX_RE.sub('', title or '')   # 先頭の既存【…】を一旦外す（無ければそのまま）
    label = region or UNKNOWN_REGION          # 判定できれば都道府県名、できなければ代替ラベル
    prefix = f'【{label}】'
    if max_length is not None:
        # 接頭辞のぶんを差し引いた文字数まで本文を切り詰める。
        # スライス [:n] は n が文字数を超えても例外にならない。
        # max(0, ...) は、接頭辞だけで max_length を超える異常系で負のスライスにならないための保険。
        base = base[:max(0, max_length - len(prefix))]

    return f'{prefix}{base}'                  # 必ず先頭に【…】を付けて返す


def strip_region_prefix(title):
    """タイトル先頭の【…】を外して返す（無ければそのまま）。
    編集フォームで、自動付与された地域ラベルを入力欄に出さないために使う。"""
    return _PREFIX_RE.sub('', title or '')

_EXTRACT_RE = re.compile(r'^\s*【([^】]*)】')  # 先頭の【…】の“中身”を取り出す（丸ごとではなくカッコ内）


def extract_region(title):
    """タイトル先頭の【…】の中身を返す（例 '【大阪府】妖怪の道' → '大阪府'）。無ければ ''。
    ルートの地域ラベルは、含まれるレポートのタイトルから地域を集めて作るため、ここで抽出する。
    （レポート作成時に既に都道府県が付いているので、座標から再判定しない）"""
    m = _EXTRACT_RE.match(title or '')
    return m.group(1) if m else ''