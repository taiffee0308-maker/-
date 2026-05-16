"""Fetch latest tech/AI news from RSS feeds and post a digest to Discord."""

from __future__ import annotations

import html
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

import feedparser
import requests

JST = timezone(timedelta(hours=9))

# Some publishers reject feedparser's default UA. Use a browser-like UA.
feedparser.USER_AGENT = (
    "Mozilla/5.0 (compatible; DailyNewsBot/1.0; +https://github.com/)"
)

FEEDS_JA: list[tuple[str, str]] = [
    ("ITmedia AI+", "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml"),
    ("Publickey", "https://www.publickey1.jp/atom.xml"),
    ("GIGAZINE", "https://gigazine.net/news/rss_2.0/"),
    ("ASCII.jp", "https://ascii.jp/rss.xml"),
]

FEEDS_EN: list[tuple[str, str]] = [
    ("Hacker News", "https://hnrss.org/frontpage?points=150"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
]

AI_KEYWORDS = (
    "ai", "ml", "llm", "gpt", "claude", "gemini", "anthropic", "openai",
    "machine learning", "deep learning", "neural", "transformer", "agent",
    "robot", "autonomous", "diffusion", "model",
    "人工知能", "機械学習", "生成ai", "ロボット", "エージェント", "モデル",
)

PER_FEED_LIMIT = 4
PER_SECTION_LIMIT = 8
LOOKBACK_HOURS = 30


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: datetime | None
    summary: str
    is_ai_related: bool


def _parse_published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
    return None


def _is_ai_related(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in AI_KEYWORDS)


def _strip_html(text: str, limit: int = 140) -> str:
    if not text:
        return ""
    no_tags = []
    in_tag = False
    for char in text:
        if char == "<":
            in_tag = True
        elif char == ">":
            in_tag = False
        elif not in_tag:
            no_tags.append(char)
    cleaned = html.unescape("".join(no_tags)).strip()
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1].rstrip() + "…"
    return cleaned


def fetch_feed(source: str, url: str, cutoff: datetime) -> list[Article]:
    parsed = feedparser.parse(url)
    articles: list[Article] = []
    for entry in parsed.entries[: PER_FEED_LIMIT * 3]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue
        published = _parse_published(entry)
        if published and published < cutoff:
            continue
        summary = _strip_html(entry.get("summary", "") or entry.get("description", ""))
        haystack = f"{title} {summary}"
        articles.append(
            Article(
                title=title,
                url=link,
                source=source,
                published=published,
                summary=summary,
                is_ai_related=_is_ai_related(haystack),
            )
        )
        if len(articles) >= PER_FEED_LIMIT:
            break
    return articles


def collect(feeds: Iterable[tuple[str, str]], cutoff: datetime) -> list[Article]:
    collected: list[Article] = []
    for source, url in feeds:
        try:
            collected.extend(fetch_feed(source, url, cutoff))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] failed to fetch {source}: {exc}", file=sys.stderr)
    collected.sort(
        key=lambda a: (not a.is_ai_related, -(a.published.timestamp() if a.published else 0))
    )
    return collected[:PER_SECTION_LIMIT]


def format_article_line(article: Article) -> str:
    tag = "🤖 " if article.is_ai_related else ""
    title = article.title.replace("[", "［").replace("]", "］")
    line = f"- {tag}[{title}]({article.url}) — *{article.source}*"
    if article.summary:
        line += f"\n  {article.summary}"
    return line


def build_message(ja: list[Article], en: list[Article]) -> str:
    today = datetime.now(JST).strftime("%Y-%m-%d (%a)")
    parts = [f"# 📰 今日の気になるテック・AIニュース ({today})"]

    if ja:
        parts.append("\n## 🇯🇵 国内")
        parts.extend(format_article_line(a) for a in ja)
    if en:
        parts.append("\n## 🌐 海外")
        parts.extend(format_article_line(a) for a in en)
    if not ja and not en:
        parts.append("\n_本日は取得できる新着記事がありませんでした。_")
    return "\n".join(parts)


def post_to_discord(webhook_url: str, content: str) -> None:
    chunks = chunk_message(content, limit=1900)
    for chunk in chunks:
        response = requests.post(
            webhook_url,
            json={"content": chunk, "allowed_mentions": {"parse": []}},
            timeout=30,
        )
        if response.status_code >= 300:
            raise RuntimeError(
                f"Discord webhook failed: {response.status_code} {response.text}"
            )


def chunk_message(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.split("\n"):
        line_len = len(line) + 1
        if current_len + line_len > limit and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def main() -> int:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    ja_articles = collect(FEEDS_JA, cutoff)
    en_articles = collect(FEEDS_EN, cutoff)
    message = build_message(ja_articles, en_articles)

    print(message)

    if not webhook:
        print("\n[info] DISCORD_WEBHOOK_URL is not set; skipping Discord post.", file=sys.stderr)
        return 0

    post_to_discord(webhook, message)
    print("\n[info] Posted digest to Discord.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
