"""Rendu déterministe des scores visibles dans le bulletin RSS."""

from __future__ import annotations


VISIBLE_SCORES = {3, 4, 5}


def render_score_details(articles: list[dict]) -> str:
    """Retourne une annexe Markdown score + raison pour les articles retenus.

    Le rendu est produit par Python, sans nouvel appel LLM, afin de garantir
    que chaque score reste associé au bon article. ``score_phase1`` est la
    référence : il représente la note initiale avant une éventuelle déduplication.
    """
    visible = []
    for position, article in enumerate(articles):
        score = _article_score(article)
        if score in VISIBLE_SCORES:
            visible.append((position, score, article))

    if not visible:
        return ""

    visible.sort(key=lambda item: (-item[1], item[0]))
    lines = ["**Évaluation du scoring**", ""]
    for _, score, article in visible:
        title = _escape_markdown(article.get("title", "Sans titre"))
        source = _escape_markdown(article.get("source", "Source inconnue"))
        reason = _escape_markdown(article.get("raison", ""))
        link = str(article.get("link", "")).strip()
        title_md = f"[{title}]({link})" if link.startswith(("https://", "http://")) else title

        line = f"- **{score}/5** — {title_md} — {source}"
        if reason:
            line += f". Raison : {reason}"
        lines.append(line)

    return "\n".join(lines)


def _article_score(article: dict) -> int | None:
    value = article.get("score_phase1", article.get("score"))
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _escape_markdown(value: object) -> str:
    text = " ".join(str(value or "").split())
    for char in ("\\", "*", "_", "[", "]"):
        text = text.replace(char, "\\" + char)
    return text
