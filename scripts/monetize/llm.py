"""Claude (Anthropic API) によるテキスト生成ラッパー。

ANTHROPIC_API_KEY が無い場合はモック文字列を返すので、キー無しでも
パイプライン全体（注文→生成→納品）を通しで試せる。
"""

from __future__ import annotations

import os
import sys

from .config import MODEL


def have_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def generate(
    system: str,
    prompt: str,
    *,
    max_tokens: int = 8000,
    effort: str = "high",
) -> str:
    """system / prompt を渡して本文テキストを返す。

    長文生成でも HTTP タイムアウトしないようストリーミングを使い、
    最後に get_final_message() で全文を受け取る。
    """
    if not have_api_key():
        return _mock(system, prompt)

    import anthropic  # 遅延 import: キー無し環境でも import エラーにしない

    client = anthropic.Anthropic()
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for _ in stream.text_stream:
                pass
            message = stream.get_final_message()
    except anthropic.APIStatusError as exc:  # noqa: BLE001
        print(f"[warn] Claude API error: {exc}", file=sys.stderr)
        raise

    return "".join(b.text for b in message.content if b.type == "text").strip()


def _mock(system: str, prompt: str) -> str:
    """API キーが無いときのダミー出力。動作確認用。"""
    return (
        "（モック出力: ANTHROPIC_API_KEY が未設定のため実際の生成は行われていません）\n\n"
        f"[system]\n{system[:200]}\n\n[prompt]\n{prompt[:400]}\n"
    )
