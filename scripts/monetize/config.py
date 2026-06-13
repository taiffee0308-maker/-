"""販売する AI サービスの定義・価格・環境設定。"""

from __future__ import annotations

import os
from dataclasses import dataclass

# --- 保存先 -----------------------------------------------------------------
DATA_DIR = os.environ.get("MONETIZE_DATA_DIR", "data")
OUTPUT_DIR = os.environ.get("MONETIZE_OUTPUT_DIR", os.path.join(DATA_DIR, "outputs"))
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")

DEFAULT_CURRENCY = "JPY"

# 使用する Claude モデル（既定: 最新の Opus）
MODEL = os.environ.get("MONETIZE_MODEL", "claude-opus-4-8")


@dataclass(frozen=True)
class Product:
    """ストアに並べる 1 商品。"""

    key: str
    title: str
    description: str
    base_price: int  # 最低料金 (JPY)
    unit: str  # 課金単位の説明（表示用）


# 商品カタログ。価格は目安。実際の最終金額は各サービスの estimate_price で算出。
CATALOG: dict[str, Product] = {
    "translation": Product(
        key="translation",
        title="AI 翻訳（日英・多言語）",
        description="用語統一・トーン指定に対応した自然な翻訳。原文を貼るだけ。",
        base_price=500,
        unit="1文字あたり 1.5円（最低 500円）",
    ),
    "seo_article": Product(
        key="seo_article",
        title="SEO 記事・ブログ生成",
        description="キーワードから構成→本文→メタディスクリプションまで一括生成。",
        base_price=2000,
        unit="1記事（〜3000字）2,000円〜",
    ),
    "logo_banner": Product(
        key="logo_banner",
        title="ロゴ・バナー生成（SVG）",
        description="ブランド情報からベクター（SVG）ロゴと配色・使用ガイドを生成。",
        base_price=3000,
        unit="1案 3,000円（追加案 +1,500円）",
    ),
    "transcription": Product(
        key="transcription",
        title="文字起こし・議事録作成",
        description="音声/文字起こしテキストを整文し、要約・議事録に変換。",
        base_price=1000,
        unit="10分あたり 1,000円〜",
    ),
}
