"""注文を受け取り、AI 生成 → 納品まで自動実行するオーケストレーション。"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from . import delivery
from .config import OUTPUT_DIR
from .orders import Order, OrderStore
from .services import get_service


def process_order(order: Order, store: OrderStore) -> Order:
    """1 件の注文を処理する。例外時は status=failed にして握りつぶさず記録。"""
    service = get_service(order.service)

    order.status = "processing"
    store.update(order)

    try:
        outputs = service.produce(order.params)
        out_dir = os.path.join(OUTPUT_DIR, order.id)
        os.makedirs(out_dir, exist_ok=True)
        for f in outputs:
            f.write_to(os.path.join(out_dir, f.name))

        order.output_dir = out_dir
        order.delivered_at = datetime.now(timezone.utc).isoformat()
        order.status = "delivered"
        store.update(order)

        delivery.deliver(order, [f.name for f in outputs])
        print(f"[ok] order {order.id} ({order.service}) delivered -> {out_dir}",
              file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        order.status = "failed"
        order.error = str(exc)
        store.update(order)
        print(f"[error] order {order.id} failed: {exc}", file=sys.stderr)

    return order


def process_pending(store: OrderStore) -> int:
    """支払い済みで未処理の注文をまとめて処理する。"""
    pending = store.pending_paid()
    if not pending:
        print("[info] 処理待ちの注文はありません。", file=sys.stderr)
        return 0
    for order in pending:
        process_order(order, store)
    return len(pending)
