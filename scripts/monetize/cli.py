"""コマンドライン: カタログ表示・注文作成・処理実行（テスト/運用兼用）。

使い方:
  python -m scripts.monetize.cli catalog
  python -m scripts.monetize.cli order --service translation \\
      -p text="こんにちは" -p target_lang=English --email me@example.com --run
  python -m scripts.monetize.cli run        # 支払い済み未処理をまとめて処理
  python -m scripts.monetize.cli list
  python -m scripts.monetize.cli serve       # Webhook サーバー起動
"""

from __future__ import annotations

import argparse
import json
import sys

from .config import CATALOG
from .orders import Order, OrderStore
from .pipeline import process_order, process_pending
from .services import get_service


def _parse_params(pairs: list[str] | None, params_json: str | None) -> dict:
    params: dict = {}
    if params_json:
        params.update(json.loads(params_json))
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"-p は key=value 形式: {pair!r}")
        key, value = pair.split("=", 1)
        params[key] = value
    return params


def cmd_catalog(_args) -> int:
    print("# 取扱サービス\n")
    for p in CATALOG.values():
        print(f"- [{p.key}] {p.title}")
        print(f"    {p.description}")
        print(f"    料金: {p.unit}\n")
    return 0


def cmd_order(args) -> int:
    params = _parse_params(args.param, args.params_json)
    service = get_service(args.service)
    order = Order.new(args.service, params, customer_email=args.email)
    order.amount = service.estimate_price(params)

    store = OrderStore()
    store.add(order)
    print(f"[ok] 注文作成 {order.id}: {args.service} 見積 {order.amount}{order.currency}",
          file=sys.stderr)

    if args.run:
        order.status = "paid"  # テスト用に支払い済み扱い
        store.update(order)
        process_order(order, store)
        if order.output_dir:
            print(order.output_dir)
    return 0 if order.status != "failed" else 1


def cmd_run(_args) -> int:
    process_pending(OrderStore())
    return 0


def cmd_list(_args) -> int:
    for o in OrderStore().all():
        print(f"{o.id}  {o.service:<14} {o.status:<10} "
              f"{o.amount}{o.currency}  {o.customer_email}")
    return 0


def cmd_serve(args) -> int:
    from .server import serve
    serve(port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="monetize")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalog", help="取扱サービス一覧").set_defaults(func=cmd_catalog)

    p_order = sub.add_parser("order", help="注文を作成（--run で即生成）")
    p_order.add_argument("--service", required=True, choices=list(CATALOG))
    p_order.add_argument("-p", "--param", action="append", help="key=value（複数可）")
    p_order.add_argument("--params-json", help="JSON 文字列でまとめて指定")
    p_order.add_argument("--email", default="")
    p_order.add_argument("--run", action="store_true", help="支払い済み扱いで即処理")
    p_order.set_defaults(func=cmd_order)

    sub.add_parser("run", help="支払い済み未処理を一括処理").set_defaults(func=cmd_run)
    sub.add_parser("list", help="注文一覧").set_defaults(func=cmd_list)

    p_serve = sub.add_parser("serve", help="Webhook サーバー起動")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
