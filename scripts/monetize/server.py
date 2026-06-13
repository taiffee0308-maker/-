"""決済 Webhook 受信サーバー（標準ライブラリのみ）。

Stripe / Gumroad の「支払い完了」通知を受けて注文を作成し、
そのまま AI 生成→納品まで自動実行する。これが「自動で販売まで持っていく」中核。

エンドポイント:
  POST /webhook/stripe   Stripe Checkout の checkout.session.completed
  POST /webhook/gumroad  Gumroad の sale ping（application/x-www-form-urlencoded）
  GET  /health           疎通確認

Stripe 側の metadata に次を入れておく想定:
  service = "translation" など / params = JSON文字列 / （顧客メールは customer_details）
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import CATALOG
from .orders import Order, OrderStore
from .pipeline import process_order

# Gumroad の商品 permalink → サービスキーの対応（環境に合わせて編集）
GUMROAD_PRODUCT_MAP = {
    "translation": "translation",
    "seo": "seo_article",
    "logo": "logo_banner",
    "minutes": "transcription",
}


class WebhookHandler(BaseHTTPRequestHandler):
    store: OrderStore  # set by serve()

    def log_message(self, fmt, *args):  # noqa: D401 - 既定ログを stderr に統一
        print("[server] " + (fmt % args), file=sys.stderr)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._respond(200, {"ok": True})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            if self.path == "/webhook/stripe":
                order = self._handle_stripe(body)
            elif self.path == "/webhook/gumroad":
                order = self._handle_gumroad(body)
            else:
                self._respond(404, {"error": "not found"})
                return
        except PermissionError as exc:
            self._respond(400, {"error": f"signature: {exc}"})
            return
        except Exception as exc:  # noqa: BLE001
            self._respond(400, {"error": str(exc)})
            return

        if order is None:
            self._respond(200, {"ignored": True})
            return

        # 注文を保存 → 即時処理（生成→納品）
        self.store.add(order)
        process_order(order, self.store)
        self._respond(200, {"order_id": order.id, "status": order.status})

    # --- Stripe -------------------------------------------------------------
    def _handle_stripe(self, body: bytes) -> Order | None:
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        if secret:
            self._verify_stripe(body, self.headers.get("Stripe-Signature", ""), secret)

        event = json.loads(body or b"{}")
        if event.get("type") != "checkout.session.completed":
            return None
        session = event["data"]["object"]
        meta = session.get("metadata") or {}
        service = meta.get("service", "")
        if service not in CATALOG:
            raise ValueError(f"metadata.service が不正: {service!r}")
        params = json.loads(meta.get("params", "{}"))
        email = (session.get("customer_details") or {}).get("email", "")

        order = Order.new(service, params, customer_email=email)
        order.status = "paid"
        order.amount = int(session.get("amount_total") or 0)
        order.currency = (session.get("currency") or "jpy").upper()
        return order

    @staticmethod
    def _verify_stripe(body: bytes, sig_header: str, secret: str) -> None:
        parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
        timestamp, v1 = parts.get("t"), parts.get("v1")
        if not timestamp or not v1:
            raise PermissionError("Stripe-Signature ヘッダが不正")
        signed = f"{timestamp}.".encode() + body
        expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, v1):
            raise PermissionError("署名検証に失敗")

    # --- Gumroad ------------------------------------------------------------
    def _handle_gumroad(self, body: bytes) -> Order | None:
        form = urllib.parse.parse_qs(body.decode("utf-8"))

        def first(key: str, default: str = "") -> str:
            return form.get(key, [default])[0]

        permalink = first("product_permalink") or first("permalink")
        service = GUMROAD_PRODUCT_MAP.get(permalink)
        if not service:
            raise ValueError(f"未対応の Gumroad 商品: {permalink!r}")

        # Gumroad の custom fields は url_params[...] / 任意キーで届く想定。
        params_raw = first("params") or "{}"
        params = json.loads(params_raw)
        email = first("email")

        order = Order.new(service, params, customer_email=email)
        order.status = "paid"
        order.amount = int(float(first("price", "0")))
        order.currency = first("currency", "USD").upper()
        return order

    # --- util ---------------------------------------------------------------
    def _respond(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    WebhookHandler.store = OrderStore()
    server = ThreadingHTTPServer((host, port), WebhookHandler)
    print(f"[server] listening on http://{host}:{port}", file=sys.stderr)
    print("[server] POST /webhook/stripe  POST /webhook/gumroad  GET /health",
          file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] shutting down", file=sys.stderr)
        server.shutdown()


if __name__ == "__main__":
    serve(port=int(os.environ.get("PORT", "8000")))
