"""文字起こし・議事録: 音声/テキストを整文し、要約・議事録に変換。

音声ファイルからの文字起こしは外部の Whisper 等が必要なため差し替え式にしている。
- OPENAI_API_KEY があり openai がインストール済みなら Whisper API を使用
- それ以外は params['transcript_text']（既存の文字起こし）を入力として受け取る
整文・要約・議事録化は Claude が担当（ここが付加価値）。
"""

from __future__ import annotations

import math
import os

from .. import llm
from ..config import CATALOG
from .base import OutputFile, Service

SYSTEM = """\
あなたは議事録のプロです。話し言葉の文字起こしを、意味を変えずに読みやすい
書き言葉へ整え、要約や議事録に構造化します。事実に無い内容は補完しません。"""


class TranscriptionService(Service):
    key = "transcription"
    title = CATALOG["transcription"].title

    def estimate_price(self, params: dict) -> int:
        minutes = float(params.get("minutes", 10))
        base = CATALOG["transcription"].base_price
        return max(base, math.ceil(minutes / 10) * base)

    def produce(self, params: dict) -> list[OutputFile]:
        raw = self._obtain_transcript(params)
        if not raw.strip():
            raise ValueError(
                "transcription には params['transcript_text'] か "
                "params['audio_path'](+Whisper) が必要です"
            )

        make_minutes = params.get("minutes_doc", True)
        make_summary = params.get("summary", True)

        sections = ["整文された全文（読みやすい書き言葉に）"]
        if make_summary:
            sections.append("3〜5行の要約")
        if make_minutes:
            sections.append("議事録（## 決定事項 / ## ToDo（担当・期限） / ## 論点）")

        prompt = (
            "次の文字起こしを処理してください。出力は Markdown で、"
            f"以下のセクションを順に含めます:\n- "
            + "\n- ".join(sections)
            + f"\n\n--- 文字起こし ---\n{raw}\n"
        )

        result = llm.generate(SYSTEM, prompt, max_tokens=12000, effort="high")
        return [OutputFile(name="minutes.md", text=result)]

    # --- 文字起こしの取得 ---------------------------------------------------
    def _obtain_transcript(self, params: dict) -> str:
        if params.get("transcript_text"):
            return params["transcript_text"]

        audio_path = params.get("audio_path")
        if audio_path and os.environ.get("OPENAI_API_KEY"):
            return self._whisper(audio_path)
        return ""

    def _whisper(self, audio_path: str) -> str:
        try:
            from openai import OpenAI  # 任意依存
        except ImportError:
            return ""
        client = OpenAI()
        with open(audio_path, "rb") as f:
            tr = client.audio.transcriptions.create(model="whisper-1", file=f)
        return tr.text
