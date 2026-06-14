# AI サービス自前ストア（注文→生成→納品 全自動）

クラウドソーシングで需要の大きい作業のうち **AI で代替しやすいもの** を商品化し、
自前の販路（Stripe / Gumroad など）からの注文を **無人で処理** するパイプラインです。

> ⚠️ **方針（重要）**
> このツールは「**自分の商品を自分の販路で売る**」ための自動化に限定しています。
> クラウドワークス等を**自動スクレイピング・自動応募**する用途には使いません
> （[利用規約](https://crowdworks.jp/pages/agreement)違反・アカウント停止リスク）。
> CrowdWorks は「どの作業に需要があるか」を**人手でリサーチする参考**に留めてください。

## 取扱サービス（AI 代替の本命）

| キー | 内容 | 使う AI |
|---|---|---|
| `translation` | 翻訳（日英・多言語、用語統一・トーン対応） | Claude |
| `seo_article` | SEO 記事・ブログ（構成→本文→メタ） | Claude |
| `logo_banner` | ロゴ・バナー（**SVG ベクター**＋使用ガイド） | Claude（SVG 直接生成） |
| `transcription` | 文字起こし整文・要約・議事録化 | Claude（+ 任意で Whisper） |

価格・単位は `config.py` の `CATALOG` で編集できます。

## アーキテクチャ

```
決済 (Stripe/Gumroad)
      │  Webhook (支払い完了)
      ▼
 server.py ──→ orders.py(注文を paid で作成)
      │
      ▼
 pipeline.py ──→ services/<種別>.py (Claude で生成)
      │
      ▼
 delivery.py (data/outputs/<注文ID>/ に保存 / SMTP があればメール送付)
```

- `llm.py`: Claude 呼び出し（`claude-opus-4-8`、ストリーミング）。**`ANTHROPIC_API_KEY` が無いとモック出力**になるので、キー無しでも全工程を試せます。

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."        # 本番生成に必須（無ければモック）
# 任意: メール納品
export SMTP_HOST="smtp.example.com" SMTP_USER="..." SMTP_PASSWORD="..." SMTP_FROM="you@example.com"
```

## 使い方（CLI）

```bash
# 取扱一覧
python -m scripts.monetize.cli catalog

# 注文を作って即生成（--run で支払い済み扱い・テスト用）
python -m scripts.monetize.cli order --service seo_article \
    -p keyword="在宅 副業 始め方" -p target_chars=3000 --email buyer@example.com --run

# 翻訳
python -m scripts.monetize.cli order --service translation \
    -p text="翻訳したい本文…" -p target_lang=English --run

# 支払い済みで未処理の注文を一括処理
python -m scripts.monetize.cli run

# 注文一覧
python -m scripts.monetize.cli list
```

成果物は `data/outputs/<注文ID>/` に出力されます（`data/` は gitignore 済み）。

## 自動販売（Webhook サーバー）

```bash
python -m scripts.monetize.cli serve --port 8000
# POST /webhook/stripe   POST /webhook/gumroad   GET /health
```

### Stripe 連携
1. Stripe Checkout / Payment Link を作成し、`metadata` に以下を設定:
   - `service` = `translation` / `seo_article` / `logo_banner` / `transcription`
   - `params` = JSON 文字列（例 `{"keyword":"...","target_chars":3000}`）
2. Webhook 宛先を `https://<your-host>/webhook/stripe` に設定
3. 署名検証のため `export STRIPE_WEBHOOK_SECRET="whsec_..."`

`checkout.session.completed` を受けると、注文作成 → 生成 → 納品まで自動実行します。

### Gumroad 連携
- 商品 permalink → サービスの対応は `server.py` の `GUMROAD_PRODUCT_MAP` を編集。
- カスタムフィールド `params`（JSON）で入力を渡します。

## 拡張ポイント

- **新サービス追加**: `services/base.py` の `Service` を継承し `services/__init__.py` の `REGISTRY` に登録。
- **画像のラスター化(PNG)**: `logo_banner.py` に画像生成 API（Adobe Firefly Services / Stability / OpenAI Images 等）を差し込む。
- **音声文字起こし**: `transcription.py` は `OPENAI_API_KEY` があれば Whisper を使用。`faster-whisper` 等のローカル実行に差し替え可。
- **決済追加**: `server.py` にエンドポイントを足す（PayPal / Lemon Squeezy 等）。
