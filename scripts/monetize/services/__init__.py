"""サービスエンジンのレジストリ。"""

from __future__ import annotations

from .base import OutputFile, Service
from .logo_banner import LogoBannerService
from .seo_article import SeoArticleService
from .transcription import TranscriptionService
from .translation import TranslationService

REGISTRY: dict[str, Service] = {
    s.key: s
    for s in (
        TranslationService(),
        SeoArticleService(),
        LogoBannerService(),
        TranscriptionService(),
    )
}


def get_service(key: str) -> Service:
    if key not in REGISTRY:
        raise ValueError(f"未知のサービス: {key}（{', '.join(REGISTRY)}）")
    return REGISTRY[key]


__all__ = ["OutputFile", "Service", "REGISTRY", "get_service"]
