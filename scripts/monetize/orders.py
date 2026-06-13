"""注文（Order）モデルと JSON ファイルによる永続化。"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .config import CATALOG, DEFAULT_CURRENCY, ORDERS_FILE

# 注文ステータスの遷移:
#   pending  -> paid -> processing -> delivered
#                                  \-> failed
STATUSES = ("pending", "paid", "processing", "delivered", "failed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Order:
    id: str
    service: str  # CATALOG のキー
    params: dict  # サービス個別の入力
    customer_email: str = ""
    status: str = "pending"
    amount: int = 0
    currency: str = DEFAULT_CURRENCY
    created_at: str = field(default_factory=_now)
    delivered_at: str | None = None
    output_dir: str | None = None
    error: str | None = None

    @staticmethod
    def new(service: str, params: dict, customer_email: str = "") -> "Order":
        if service not in CATALOG:
            raise ValueError(f"未知のサービス: {service}（{', '.join(CATALOG)}）")
        return Order(
            id=uuid.uuid4().hex[:12],
            service=service,
            params=params,
            customer_email=customer_email,
        )


class OrderStore:
    """注文を JSON ファイルに保存する素朴なストア。"""

    def __init__(self, path: str = ORDERS_FILE):
        self.path = path
        self._orders: dict[str, Order] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        with open(self.path, encoding="utf-8") as f:
            raw = json.load(f)
        self._orders = {o["id"]: Order(**o) for o in raw}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(o) for o in self._orders.values()], f,
                      ensure_ascii=False, indent=2)

    def add(self, order: Order) -> Order:
        self._orders[order.id] = order
        self._save()
        return order

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def update(self, order: Order) -> None:
        self._orders[order.id] = order
        self._save()

    def pending_paid(self) -> list[Order]:
        """処理待ち（支払い済みで未納品）の注文。"""
        return [o for o in self._orders.values() if o.status == "paid"]

    def all(self) -> list[Order]:
        return list(self._orders.values())
