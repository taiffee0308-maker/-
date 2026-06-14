"""SEO 記事生成: キーワードから構成・本文・メタ情報まで一括生成。"""

from __future__ import annotations

from .. import llm
from ..config import CATALOG
from .base import OutputFile, Service

SYSTEM = """\
あなたは SEO に精通した日本語のプロライターです。検索意図を満たし、
読者にとって有益で具体的な記事を書きます。E-E-A-T を意識し、誇張・虚偽の
断定は避けます。出力は指定の Markdown 構成に厳密に従ってください。"""


class SeoArticleService(Service):
    key = "seo_article"
    title = CATALOG["seo_article"].title

    def estimate_price(self, params: dict) -> int:
        target_chars = int(params.get("target_chars", 3000))
        base = CATALOG["seo_article"].base_price
        # 3000字を基準に、超過分は1000字ごとに+500円
        extra = max(0, target_chars - 3000)
        return base + (extra // 1000) * 500

    def produce(self, params: dict) -> list[OutputFile]:
        keyword = params.get("keyword", "").strip()
        if not keyword:
            raise ValueError("seo_article には params['keyword'] が必要です")
        target_chars = int(params.get("target_chars", 3000))
        audience = params.get("audience", "一般読者")
        tone = params.get("tone", "丁寧で分かりやすい")

        prompt = (
            f"次の条件で SEO 記事を書いてください。\n"
            f"- 主軸キーワード: {keyword}\n"
            f"- 想定読者: {audience}\n"
            f"- トーン: {tone}\n"
            f"- 目安文字数: {target_chars}字程度\n\n"
            "出力フォーマット（この見出し構成を厳守）:\n"
            "# (魅力的なタイトル / 32字前後)\n\n"
            "> メタディスクリプション: (120字以内)\n\n"
            "## はじめに\n...\n\n"
            "## (本文の見出しを複数 h2/h3 で展開)\n...\n\n"
            "## まとめ\n...\n\n"
            "---\n"
            "### 内部メモ\n- 想定検索意図:\n- 関連キーワード候補(5個):\n"
        )

        article = llm.generate(SYSTEM, prompt, max_tokens=16000, effort="high")
        return [OutputFile(name="article.md", text=article)]
