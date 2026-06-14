"""サービスエンジンの共通インターフェース。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OutputFile:
    """納品ファイル 1 個。text か data のどちらかを持つ。"""

    name: str
    text: str | None = None
    data: bytes | None = None

    def write_to(self, path: str) -> None:
        if self.data is not None:
            with open(path, "wb") as f:
                f.write(self.data)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text or "")


class Service:
    """各 AI サービスはこれを継承する。"""

    key: str = ""
    title: str = ""

    def estimate_price(self, params: dict) -> int:
        """入力から最終金額 (JPY) を見積もる。"""
        raise NotImplementedError

    def produce(self, params: dict) -> list[OutputFile]:
        """成果物ファイルのリストを生成して返す。"""
        raise NotImplementedError
