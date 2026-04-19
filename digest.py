"""Pipeline de curation : OPML -> fetch RSS -> scoring Haiku
-> synthèse Sonnet -> RSS de sortie."""

import hashlib
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
from anthropic import Anthropic
from feedgen.feed import FeedGenerator

from prompt import SCORING_PROMPT, SYNTHESIS_PROMPT

# ---- Configuration -----------------------------------------------------------

OPML_FILE = "sources.opml"
SEEN_FILE = "seen.json"
OUTPUT_FILE = "output/digest.xml"
DIGEST_URL = "https://julienoh.github.io/veille-ia/digest.xml"  # à ajuster

LOOKBACK_HOURS = 8           # on ne regarde que les articles des 8 dernières heures
MIN_SCORE = 3                 # seuil pour passer dans le digest
MAX_ARTICLES_PER_CATEGORY = 20  # garde-fou coût API
SEEN_RETENTION_DAYS = 14     # on nettoie seen.json au-delà

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

client = Anthropic()  # lit ANTHROPIC_API_KEY depuis l'env

# ---- OPML parsing ------------------------------------------------------------

def load_sources(opml_path: str) -> list[dict]:
    """Retourne [{'title', 'xmlUrl', 'category'}, ...] depuis l'OPML."""
    tree = ET.parse(opml_path)
    out = []
    for category in tree.findall("./body/outline"):
        cat_name = category.get("text", "Autre")
        for feed in category.findall("./outline[@xmlUrl]"):
            out.append({
                "title": feed.get("text") or feed.get("title") or "?",
                "xmlUrl": feed.get("xmlUrl"),
                "category": cat_name,
            })
    return out

# ---- Seen storage (dedup) ----------------------------------------------------

def load_seen() -> dict:
    """seen = {hash: iso_date_vu}. On le commit dans le repo."""
    if not Path(SEEN_FILE).exists():
        return {}
    with open(SEEN_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_seen(seen: dict) -> None:
    # Nettoyage : on retire les entrées > SEEN_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_RETENTION_DAYS)
    seen = {h: d for h, d in seen.items()
            if datetime.fromisoformat(d) > cutoff}
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)

def article_hash(entry) -> str:
    """Hash stable : on prend l'URL si dispo, sinon titre normalisé."""
    key = entry.get("link") or entry.get("title", "").strip().lower()
    return hashlib.sha1(key.encode()).hexdigest()[:12]

# ---- Fetching ----------------------------------------------------------------

def fetch_recent_articles(sources: list[dict], seen: dict) -> list[dict]:
    """Récupère les entrées récentes non déjà vues."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    articles = []

    for src in sources:
        try:
            parsed = feedparser.parse(src["xmlUrl"])
        except Exception as e:
            print(f"  ! fetch error {src['title']}: {e}", file=sys.stderr)
            continue

        for entry in parsed.entries:
            # Filtre date : on utilise published_parsed ou updated_parsed
            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            if ts:
                published = datetime(*ts[:6], tzinfo=timezone.utc)
                if published < cutoff:
                    continue
            # Pas de date : on prend quand même mais c'est risqué

            h = article_hash(entry)
            if h in seen:
                continue

            # Nettoyage du résumé (strip HTML basique)
            summary = entry.get("summary") or entry.get("description") or ""
            summary = re.sub(r"<[^>]+>", " ", summary)
            summary = re.sub(r"\s+", " ", summary).strip()[:800]

            articles.append({
                "hash": h,
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", ""),
                "summary": summary,
                "source": src["title"],
                "category": src["category"],
                "published": entry.get("published", ""),
            })

    return articles

# ---- Scoring avec Haiku ------------------------------------------------------

def score_article(article: dict) -> dict | None:
    """Renvoie {'score': int, 'tag': str} ou None si erreur."""
    try:
        resp = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": SCORING_PROMPT.format(
                    title=article["title"],
                    source=article["source"],
                    summary=article["summary"][:400],
                ),
            }],
        )
        text = resp.content[0].text.strip()
        # Le modèle peut parfois ajouter du texte autour, on isole le JSON
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group(0))
        return {"score": int(data["score"]), "tag": data.get("tag", "autre")}
    except Exception as e:
        print(f"  ! scoring error: {e}", file=sys.stderr)
        return None

# ---- Synthèse avec Sonnet ----------------------------------------------------

def synthesize(category: str, articles: list[dict]) -> str:
    """Génère le Markdown d'une section du digest."""
    articles_txt = "\n\n".join(
        f"- Titre : {a['title']}\n  Source : {a['source']} ({a['link']})\n"
        f"  Résumé : {a['summary'][:300]}"
        for a in articles
    )
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": SYNTHESIS_PROMPT.format(
                category=category,
                period=f"dernières {LOOKBACK_HOURS}h",
                articles=articles_txt,
            ),
        }],
    )
    return resp.content[0].text.strip()

# ---- Génération du flux RSS --------------------------------------------------

def write_rss(sections: dict[str, str]) -> None:
    """Un item RSS par exécution, contenant tout le digest."""
    fg = FeedGenerator()
    fg.id(DIGEST_URL)
    fg.title("Veille IA & Cyber — Digest perso")
    fg.link(href=DIGEST_URL, rel="self")
    fg.description("Digest IA et cybersécurité généré par Claude")
    fg.language("fr")

    # On ne produit qu'un seul item par run (le digest courant)
    now = datetime.now(timezone.utc)
    content_md = "\n\n".join(sections.values())

    fe = fg.add_entry()
    fe.id(f"{DIGEST_URL}#{now.strftime('%Y%m%d-%H%M')}")
    fe.title(f"Digest — {now.strftime('%d/%m %Hh')}")
    fe.link(href=DIGEST_URL)
    fe.pubDate(now)
    # On met le markdown dans description ET content:encoded
    # Reeder rendra le Markdown comme texte — on peut aussi convertir en HTML
    fe.description(content_md)
    fe.content(md_to_html(content_md), type="CDATA")

    Path("output").mkdir(exist_ok=True)
    fg.rss_file(OUTPUT_FILE, pretty=True)

def md_to_html(md: str) -> str:
    """Conversion minimale Markdown -> HTML (pas de dépendance externe)."""
    html = md
    html = re.sub(r"## (.+)", r"<h2>\1</h2>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)
    # Bullet list
    lines = html.split("\n")
    out = []
    in_list = False
    for line in lines:
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{line[2:]}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(line)
    if in_list:
        out.append("</ul>")
    return "\n".join(out)

# ---- Main --------------------------------------------------------------------

def main():
    print(f"=== Digest run {datetime.now().isoformat()} ===")

    sources = load_sources(OPML_FILE)
    print(f"Sources chargées : {len(sources)}")

    seen = load_seen()
    articles = fetch_recent_articles(sources, seen)
    print(f"Articles frais trouvés : {len(articles)}")

    if not articles:
        print("Rien de neuf, on sort.")
        return

    # Scoring
    scored = []
    for i, a in enumerate(articles):
        if i % 20 == 0:
            print(f"  scoring {i}/{len(articles)}")
        result = score_article(a)
        seen[a["hash"]] = datetime.now(timezone.utc).isoformat()
        if result and result["score"] >= MIN_SCORE:
            a.update(result)
            scored.append(a)

    print(f"Articles retenus (score >= {MIN_SCORE}) : {len(scored)}")

    if not scored:
        save_seen(seen)
        print("Rien de pertinent, on sort.")
        return

    # Regroupement par catégorie, cap par catégorie
    by_cat = defaultdict(list)
    for a in scored:
        by_cat[a["category"]].append(a)
    for cat in by_cat:
        by_cat[cat] = sorted(by_cat[cat], key=lambda x: -x["score"])[:MAX_ARTICLES_PER_CATEGORY]

    # Synthèse
    sections = {}
    for cat, items in by_cat.items():
        print(f"  synthèse {cat} ({len(items)} articles)")
        sections[cat] = synthesize(cat, items)

    # Écriture
    write_rss(sections)
    save_seen(seen)
    print(f"✓ Digest écrit dans {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
