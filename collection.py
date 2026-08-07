"""Garde-fous de collecte appliqués avant tout appel LLM."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone


def compute_collection_cutoff(
    now: datetime,
    last_success: datetime | None,
    *,
    initial_lookback_hours: int,
    overlap_minutes: int,
) -> datetime:
    """Calcule le début de la fenêtre sans trou entre deux runs réussis.

    Le dernier run réussi est la référence, et non l'heure théorique du cron :
    un run retardé ou manqué ne crée donc pas de période aveugle. Un léger
    chevauchement est volontaire ; ``seen.json`` absorbe les doublons.
    """
    if now.tzinfo is None:
        raise ValueError("now doit être timezone-aware")

    if last_success is not None:
        if last_success.tzinfo is None:
            last_success = last_success.replace(tzinfo=timezone.utc)
        if last_success <= now:
            return last_success - timedelta(minutes=overlap_minutes)

    return now - timedelta(hours=initial_lookback_hours)


def limit_articles(
    articles: list[dict],
    *,
    max_per_source: int,
    max_total: int,
) -> tuple[list[dict], dict[str, int]]:
    """Priorise les plus récents et applique les plafonds avant le scoring.

    Les articles sans date passent après les articles datés. Les éléments
    écartés ne sont pas modifiés et ne doivent pas être ajoutés à ``seen.json``.
    """
    if max_per_source < 1 or max_total < 1:
        raise ValueError("les plafonds doivent être strictement positifs")

    indexed = list(enumerate(articles))
    indexed.sort(key=lambda pair: (-_published_timestamp(pair[1]), pair[0]))

    selected: list[dict] = []
    per_source: Counter[str] = Counter()
    dropped_per_source = 0
    dropped_global = 0

    for _, article in indexed:
        source = article.get("source", "?")
        if per_source[source] >= max_per_source:
            dropped_per_source += 1
            continue
        if len(selected) >= max_total:
            dropped_global += 1
            continue
        selected.append(article)
        per_source[source] += 1

    return selected, {
        "per_source": dropped_per_source,
        "global": dropped_global,
        "total": dropped_per_source + dropped_global,
    }


def _published_timestamp(article: dict) -> float:
    value = article.get("published_at", "")
    if not value:
        return float("-inf")
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError):
        return float("-inf")
