# Daily Tech/AI News Digest

毎朝 07:00 JST に、テクノロジー・AI 関連のニュースを RSS から集約して Discord に投稿します。

## 仕組み

- `scripts/daily_news.py` が日本語/英語のテック系 RSS フィード (ITmedia AI+, Publickey, GIGAZINE, Hacker News, TechCrunch, The Verge, Ars Technica, MIT Tech Review など) を取得
- AI 関連キーワードを含む記事を優先 (🤖 マーク)
- セクションごとに最大 8 件をまとめ、Discord Webhook に Markdown で投稿
- `.github/workflows/daily-news.yml` が GitHub Actions の cron (`0 22 * * *` UTC = 07:00 JST) で自動実行

## セットアップ

1. **Discord Webhook URL を作成**
   - Discord サーバーの 該当チャンネル → 「チャンネルの編集」→「連携サービス」→「ウェブフック」→「新しいウェブフック」
   - URL をコピー

2. **GitHub Secret に登録**
   - リポジトリ Settings → Secrets and variables → Actions → `New repository secret`
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: コピーした Webhook URL

3. **動作確認**
   - Actions タブ → `Daily Tech/AI News Digest` → `Run workflow` で手動実行
   - Discord にダイジェストが届けば成功

## ローカル実行 (テスト)

```bash
pip install -r requirements.txt

# stdout に出力するだけ (Webhook URL なし)
python scripts/daily_news.py

# 実際に Discord に投稿
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." python scripts/daily_news.py
```

## カスタマイズ

`scripts/daily_news.py` 冒頭の以下を編集:

- `FEEDS_JA` / `FEEDS_EN`: 対象 RSS フィード
- `AI_KEYWORDS`: 優先表示するキーワード
- `PER_FEED_LIMIT` / `PER_SECTION_LIMIT`: 取得件数
- `LOOKBACK_HOURS`: 何時間前までの記事を対象にするか

配信時刻を変更する場合は `.github/workflows/daily-news.yml` の cron 式を UTC で指定。
