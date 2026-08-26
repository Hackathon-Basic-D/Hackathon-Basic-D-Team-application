# from django.test import TestCase

# Create your tests here.
from django.test import SimpleTestCase
from users.regions import prefecture_of, with_region_prefix, extract_region, UNKNOWN_REGION


class RegionsUnitTest(SimpleTestCase):
    """users/regions.py の判定ロジックの単体テスト（DB不要）。
    prefecture_of は実際の GeoJSON を読むため static/japan_prefectures.geojson が必要。"""

    # --- prefecture_of：座標 → 都道府県名 ---

    def test_prefecture_of_osaka(self):
        # 大阪城あたりの座標 → 大阪府
        self.assertEqual(prefecture_of(34.687315, 135.526201), '大阪府')

    def test_prefecture_of_kyoto(self):
        # 京都駅あたりの座標 → 京都府
        self.assertEqual(prefecture_of(34.985849, 135.758767), '京都府')

    def test_prefecture_of_sea_returns_empty(self):
        # どの都道府県にも入らない海上 → ''
        self.assertEqual(prefecture_of(30.0, 145.0), '')

    def test_prefecture_of_invalid_returns_empty(self):
        # 数値化できない値・None → ''
        self.assertEqual(prefecture_of(None, None), '')
        self.assertEqual(prefecture_of('abc', 'xyz'), '')

    # --- with_region_prefix：タイトル先頭の地域ラベル ---
    def test_with_region_prefix_adds(self):
        # 先頭に【…】が無いタイトルに、地域ラベルを付ける
        self.assertEqual(with_region_prefix('道', '大阪府'), '【大阪府】道')

    def test_with_region_prefix_no_double(self):
        # 既に【…】が付いていても二重にしない（付け直す）
        self.assertEqual(with_region_prefix('【京都府】道', '大阪府'), '【大阪府】道')

    def test_with_region_prefix_empty_uses_fallback(self):
        # region が空なら UNKNOWN_REGION（その他）が付く
        self.assertEqual(with_region_prefix('道', ''), f'【{UNKNOWN_REGION}】道')

    def test_with_region_prefix_normalizes(self):
        # 手入力の【大阪】も、座標由来の【大阪府】に置き換わる
        self.assertEqual(with_region_prefix('【大阪】道', '大阪府'), '【大阪府】道')

    # --- extract_region：タイトル先頭の【…】の中身 ---

    def test_extract_region_found(self):
        # 先頭の【…】の中身（都道府県名）を取り出す
        self.assertEqual(extract_region('【大阪府】道'), '大阪府')

    def test_extract_region_none(self):
        # 先頭に【…】が無ければ ''
        self.assertEqual(extract_region('道'), '')
    
    # --- 複数地域の連結（ルートのラベル：大阪府・京都府 のような形） ---

    def test_with_region_prefix_multi_region(self):
        # 「・」で連結した複数地域も、そのまま先頭に付く
        self.assertEqual(with_region_prefix('道', '大阪府・京都府'), '【大阪府・京都府】道')

    def test_extract_region_multi_region(self):
        # 複数地域の【…】は、中身を連結文字列のまま取り出す
        self.assertEqual(extract_region('【大阪府・京都府】道'), '大阪府・京都府')

    # --- 空・境界のケース ---
    def test_with_region_prefix_empty_title(self):
        # 本文タイトルが空でも、地域ラベルだけは付く
        self.assertEqual(with_region_prefix('', '大阪府'), '【大阪府】')

    def test_extract_region_empty_brackets(self):
        # 中身が空の【】は、地域なし（''）として扱う
        self.assertEqual(extract_region('【】道'), '')

    # --- MultiPolygon（離島のある県）の判定 ---
    def test_prefecture_of_okinawa_island(self):
        # 那覇（沖縄本島）の座標 → 沖縄県。離島県=MultiPolygon の判定が効くかの確認。
        self.assertEqual(prefecture_of(26.2124, 127.6809), '沖縄県')