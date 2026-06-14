"""ロゴ・バナー生成: ブランド情報からベクター(SVG)ロゴと使用ガイドを生成。

ベクター(SVG)なので Claude が直接マークアップを生成でき、外部の画像生成 API
無しで実際に納品可能なファイルが得られる。ラスター(PNG)が必要な場合は
IMAGE_PROVIDER を差し替えるための拡張ポイントを残してある。
"""

from __future__ import annotations

import re

from .. import llm
from ..config import CATALOG
from .base import OutputFile, Service

SYSTEM = """\
あなたはブランドデザイナー兼 SVG コーダーです。要件に合うミニマルで
洗練されたロゴを、手書きの SVG マークアップで作成します。
- viewBox を必ず指定し、単体で表示できる完結した <svg> を出力する
- フォントは web セーフ/汎用指定にする
- 配色はブランドに合うものを選ぶ"""

# Claude の応答から ```svg ... ``` または素の <svg>...</svg> を抜き出す
_SVG_RE = re.compile(r"<svg\b.*?</svg>", re.DOTALL | re.IGNORECASE)


class LogoBannerService(Service):
    key = "logo_banner"
    title = CATALOG["logo_banner"].title

    def estimate_price(self, params: dict) -> int:
        base = CATALOG["logo_banner"].base_price
        variants = max(1, int(params.get("variants", 1)))
        return base + (variants - 1) * 1500

    def produce(self, params: dict) -> list[OutputFile]:
        brand = params.get("brand_name", "").strip()
        if not brand:
            raise ValueError("logo_banner には params['brand_name'] が必要です")
        industry = params.get("industry", "")
        style = params.get("style", "モダン・ミニマル")
        colors = params.get("colors", "おまかせ")
        kind = params.get("kind", "logo")  # logo / banner
        size = "1200x630 (OGP バナー)" if kind == "banner" else "512x512 (正方ロゴ)"

        prompt = (
            f"ブランド「{brand}」の{kind}を作成してください。\n"
            f"- 業種: {industry}\n"
            f"- スタイル: {style}\n"
            f"- 配色の希望: {colors}\n"
            f"- 推奨サイズ/viewBox: {size}\n\n"
            "次の2部構成で出力してください:\n"
            "1) ```svg ... ``` のコードブロックで完結した SVG\n"
            "2) 「## デザイン意図」「## 配色(HEX)」「## 使用上の注意」を含む簡潔な解説\n"
        )

        response = llm.generate(SYSTEM, prompt, max_tokens=8000, effort="high")

        outputs: list[OutputFile] = []
        match = _SVG_RE.search(response)
        if match:
            outputs.append(OutputFile(name="logo.svg", text=match.group(0)))
        outputs.append(OutputFile(name="brief.md", text=response))
        return outputs
