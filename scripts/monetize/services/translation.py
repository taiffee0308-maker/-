"""翻訳サービス: 原文を自然な訳文へ。用語統一・トーン指定対応。"""

from __future__ import annotations

from .. import llm
from ..config import CATALOG
from .base import OutputFile, Service

PRICE_PER_CHAR = 1.5  # JPY/文字

SYSTEM = """\
あなたはプロの翻訳者です。原文の意味・ニュアンス・固有名詞を正確に保ちつつ、
ターゲット言語として自然で読みやすい訳文を作成します。出力は訳文のみとし、
前置きや解説は書きません。"""


class TranslationService(Service):
    key = "translation"
    title = CATALOG["translation"].title

    def estimate_price(self, params: dict) -> int:
        text = params.get("text", "")
        base = CATALOG["translation"].base_price
        return max(base, int(len(text) * PRICE_PER_CHAR))

    def produce(self, params: dict) -> list[OutputFile]:
        text = params.get("text", "").strip()
        if not text:
            raise ValueError("translation には params['text'] が必要です")
        source = params.get("source_lang", "auto")
        target = params.get("target_lang", "English")
        tone = params.get("tone", "natural")
        glossary = params.get("glossary", {})  # {原語: 訳語}

        prompt = (
            f"次のテキストを {target} に翻訳してください。\n"
            f"- 元言語: {source}\n"
            f"- トーン: {tone}\n"
        )
        if glossary:
            terms = "\n".join(f"  {k} → {v}" for k, v in glossary.items())
            prompt += f"- 以下の用語訳で統一:\n{terms}\n"
        prompt += f"\n--- 原文 ---\n{text}\n"

        translated = llm.generate(SYSTEM, prompt, max_tokens=8000, effort="medium")
        body = (
            f"# 翻訳結果 ({source} → {target})\n\n"
            f"{translated}\n\n"
            f"---\n_原文文字数: {len(text)}_\n"
        )
        return [OutputFile(name="translation.md", text=body)]
