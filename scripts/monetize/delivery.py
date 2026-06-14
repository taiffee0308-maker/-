"""納品: 成果物の保存・通知。

既定ではローカル保存のみ。SMTP の環境変数が揃っていれば顧客へメール送付する。
"""

from __future__ import annotations

import os
import smtplib
import sys
from email.message import EmailMessage


def deliver(order, filenames: list[str]) -> None:
    """納品処理。メール設定があれば送る、無ければ保存パスを案内するだけ。"""
    host = os.environ.get("SMTP_HOST")
    if host and order.customer_email:
        try:
            _send_email(order, filenames, host)
            print(f"[info] order {order.id}: 顧客 {order.customer_email} にメール送付",
                  file=sys.stderr)
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] order {order.id}: メール送付失敗: {exc}", file=sys.stderr)

    print(f"[info] order {order.id}: 成果物は {order.output_dir} に保存済み "
          f"({', '.join(filenames)})", file=sys.stderr)


def _send_email(order, filenames: list[str], host: str) -> None:
    msg = EmailMessage()
    msg["From"] = os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", ""))
    msg["To"] = order.customer_email
    msg["Subject"] = f"【納品】ご注文 {order.id} の成果物をお届けします"
    msg.set_content(
        "ご注文ありがとうございます。\n"
        f"ご依頼（{order.service}）の成果物を添付いたします。\n\n"
        "ご確認のほどよろしくお願いいたします。"
    )
    for name in filenames:
        path = os.path.join(order.output_dir, name)
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application",
                               subtype="octet-stream", filename=name)

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
