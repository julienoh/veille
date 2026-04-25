"""Pipeline de curation RSS : OPML → fetch → scoring Haiku → synthèse Sonnet → RSS.

Vue d'ensemble du flux (un run = une exécution déclenchée par GitHub Actions) :

    1. load_sources()           Lit sources.opml et retourne la liste des feeds
    2. fetch_recent_articles()  feedparser sur chaque feed, filtre par date
                                (LOOKBACK_HOURS) et déduplication via seen.json
    3. score_article()          Appel Haiku par article → JSON {score, tag, raison}
                                Filtre les articles dont score >= MIN_SCORE
    4. synthesize()             Appel Sonnet par catégorie OPML → Markdown éditorial
    5. write_rss()              Génère output/digest.xml (1 item RSS contenant
                                toutes les sections concaténées)
    6. save_seen()              Persiste seen.json avec rétention SEEN_RETENTION_DAYS

Effets de bord persistés (commités dans le repo par le workflow Actions) :
- output/digest.xml  : le flux servi par GitHub Pages
- seen.json          : dictionnaire {hash: date_iso} des articles déjà traités

Tous les paramètres ajustables sont regroupés dans la section Configuration ci-dessous.
Les deux prompts Claude vivent dans prompt.py pour pouvoir itérer dessus
indépendamment du code (historique git séparé).
"""

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
# Tous les paramètres ajustables du pipeline sont regroupés ici.
# Voir README.md §6 "Paramètres de tuning" pour la sémantique de chacun.

# Chemins (relatifs au cwd, qui est la racine du repo en CI comme en local)
OPML_FILE = "sources.opml"           # Source de vérité des feeds (53 sources)
SEEN_FILE = "seen.json"              # Dédoublonnage persistant {hash: iso_date}
OUTPUT_FILE = "output/digest.xml"    # Flux RSS généré, servi par GitHub Pages
DIGEST_URL = "https://julienoh.github.io/veille/digest.xml"  # URL publique du flux

# Comportement du pipeline
LOOKBACK_HOURS = 8                # Fenêtre temporelle des articles à considérer.
                                  # Les 3 runs/jour (8h d'écart) se recouvrent
                                  # légèrement → pas de trou en cas de retard cron.
MIN_SCORE = 3                     # Seuil de pertinence Haiku (1-5). Tout article
                                  # scoré < MIN_SCORE est jeté avant la synthèse.
MAX_ARTICLES_PER_CATEGORY = 20    # Garde-fou contre les pics de volume (ex: arXiv)
                                  # qui exploseraient la facture Sonnet.
SEEN_RETENTION_DAYS = 14          # Fenêtre de déduplication. Au-delà, l'entrée
                                  # est purgée → un article peut réapparaître après.

# Modèles Claude utilisés. Mettre à jour quand Anthropic publie de nouvelles versions.
HAIKU_MODEL = "claude-haiku-4-5-20251001"   # Scoring (tâche simple, JSON court)
SONNET_MODEL = "claude-sonnet-4-6"          # Synthèse éditoriale (nuance, ton)

# Le SDK lit ANTHROPIC_API_KEY depuis l'environnement.
# En CI : injecté via GitHub Secrets. En local : export shell.
client = Anthropic()

# ---- OPML parsing ------------------------------------------------------------

def load_sources(opml_path: str) -> list[dict]:
    """Parse l'OPML et retourne la liste à plat des feeds.

    Structure attendue : <body><outline text="Catégorie"><outline xmlUrl="..." text="..."/></outline></body>
    Les outlines sans xmlUrl (sources documentées sans RSS) sont ignorées
    silencieusement grâce au sélecteur XPath `[@xmlUrl]`.

    Returns:
        Liste de dicts {'title', 'xmlUrl', 'category'}, un par feed actif.
    """
    tree = ET.parse(opml_path)
    out = []
    # Premier niveau d'outline = catégories ; deuxième = feeds individuels.
    for category in tree.findall("./body/outline"):
        cat_name = category.get("text", "Autre")
        for feed in category.findall("./outline[@xmlUrl]"):
            out.append({
                # Selon les éditeurs OPML, le nom est dans @text ou @title.
                "title": feed.get("text") or feed.get("title") or "?",
                "xmlUrl": feed.get("xmlUrl"),
                "category": cat_name,
            })
    return out

# ---- Seen storage (dedup) ----------------------------------------------------
# seen.json est commité dans le repo à chaque run par le workflow Actions
# (avec [skip ci] pour éviter une boucle de déclenchement). Cf. README §10.

def load_seen() -> dict:
    """Charge seen.json. Renvoie un dict vide au premier run."""
    if not Path(SEEN_FILE).exists():
        return {}
    with open(SEEN_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_seen(seen: dict) -> None:
    """Écrit seen.json après avoir purgé les entrées plus vieilles que la rétention.

    Le nettoyage est fait à l'écriture (pas à la lecture) pour qu'un run
    qui plante avant ce point ne perde pas son état de déduplication.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_RETENTION_DAYS)
    seen = {h: d for h, d in seen.items()
            if datetime.fromisoformat(d) > cutoff}
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)

def article_hash(entry) -> str:
    """Hash stable pour identifier un article de façon idempotente.

    On préfère l'URL (canonique chez la plupart des éditeurs). En fallback on
    prend le titre normalisé — moins fiable mais évite de dédupliquer à zéro
    quand un feed mal formé n'a pas de <link>.
    Tronqué à 12 caractères : 16^12 collisions ≈ négligeable sur ~50 articles/run.
    """
    key = entry.get("link") or entry.get("title", "").strip().lower()
    return hashlib.sha1(key.encode()).hexdigest()[:12]

# ---- Fetching ----------------------------------------------------------------

def fetch_recent_articles(sources: list[dict], seen: dict) -> list[dict]:
    """Itère sur tous les feeds, filtre par date et déduplication.

    Une exception sur un feed (404, timeout, XML malformé) est loggée sur stderr
    et n'arrête pas le pipeline — on continue avec les autres sources.

    Args:
        sources: liste produite par load_sources()
        seen:    dict des hashes déjà traités (lecture seule ici)

    Returns:
        Liste de dicts décrivant chaque article frais à scorer.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    articles = []

    for src in sources:
        try:
            parsed = feedparser.parse(src["xmlUrl"])
        except Exception as e:
            # On veut survivre à un feed cassé : log + on passe au suivant.
            print(f"  ! fetch error {src['title']}: {e}", file=sys.stderr)
            continue

        for entry in parsed.entries:
            # Filtre temporel. published_parsed est un time.struct_time UTC selon
            # la spec feedparser. On retombe sur updated_parsed si l'éditeur
            # ne fournit que la date de mise à jour.
            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            if ts:
                published = datetime(*ts[:6], tzinfo=timezone.utc)
                if published < cutoff:
                    continue
            # Pas de date → on garde l'entrée par défaut. Risque : un feed sans
            # dates pourrait nous resservir son archive entière, mais le filtre
            # `seen` évite que ça arrive plus d'une fois.

            h = article_hash(entry)
            if h in seen:
                continue

            # Nettoyage du résumé : strip HTML basique + collapse whitespace.
            # Limité à 800 chars car (a) on n'envoie que 400 à Haiku derrière,
            # (b) certains feeds renvoient l'article complet en summary.
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
    """Demande à Haiku un score 1-5 et un tag thématique pour un article.

    Le prompt impose un JSON strict {score, tag, raison}. En pratique, le modèle
    ajoute parfois du texte autour (« Voici le JSON : {...} ») — on extrait le
    premier objet JSON via regex pour rester robuste.

    Returns:
        {'score': int, 'tag': str} ou None si l'appel/parse échoue.
        None est traité par le caller comme "pas retenu" (ne casse pas le run).
    """
    try:
        resp = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=150,  # JSON court → cap bas = filet de sécurité coût/temps
            messages=[{
                "role": "user",
                "content": SCORING_PROMPT.format(
                    title=article["title"],
                    source=article["source"],
                    # 400 chars suffisent pour décider de la pertinence,
                    # et limitent la facture Haiku sur 50 articles × 3 runs/j.
                    summary=article["summary"][:400],
                ),
            }],
        )
        text = resp.content[0].text.strip()
        # Extraction du premier objet JSON présent dans la réponse.
        # DOTALL pour matcher les newlines à l'intérieur de l'objet.
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group(0))
        return {"score": int(data["score"]), "tag": data.get("tag", "autre")}
    except Exception as e:
        # On loggue mais on n'échoue pas le run pour un seul article.
        print(f"  ! scoring error: {e}", file=sys.stderr)
        return None

# ---- Synthèse avec Sonnet ----------------------------------------------------

def synthesize(category: str, articles: list[dict]) -> str:
    """Demande à Sonnet une synthèse Markdown éditoriale d'une catégorie.

    Un appel par catégorie OPML (vs un appel global) → meilleur regroupement
    thématique et permet d'ajuster le ton par catégorie si besoin via le prompt.

    Args:
        category: nom de la catégorie OPML (ex: "Sources françaises IA")
        articles: liste d'articles déjà filtrés et triés par score décroissant

    Returns:
        Markdown brut, à concaténer ensuite avec les autres sections.
    """
    # Format compact lisible pour le modèle. 300 chars de résumé suffisent
    # ici car Sonnet n'a pas besoin de tout le contenu pour synthétiser.
    articles_txt = "\n\n".join(
        f"- Titre : {a['title']}\n  Source : {a['source']} ({a['link']})\n"
        f"  Résumé : {a['summary'][:300]}"
        for a in articles
    )
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2000,  # ~3-4 paragraphes Markdown, large marge
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
    """Génère output/digest.xml avec UN SEUL item contenant tout le digest.

    Choix éditorial (cf. README §10) : on veut un format "bulletin" — Reeder
    affiche "1 nouveau bulletin" 3x/jour, plutôt qu'une liste de N items
    atomiques à marquer lus un par un.

    Args:
        sections: {nom_catégorie: markdown_synthèse} produit par synthesize()
    """
    fg = FeedGenerator()
    fg.id(DIGEST_URL)
    fg.title("Veille IA & Cyber — Digest perso")
    fg.link(href=DIGEST_URL, rel="self")
    fg.description("Digest IA et cybersécurité généré par Claude")
    fg.language("fr")

    now = datetime.now(timezone.utc)
    # Concaténation simple : l'ordre des sections suit l'ordre d'insertion
    # dans le dict (Python 3.7+ garantit l'ordre).
    content_md = "\n\n".join(sections.values())

    fe = fg.add_entry()
    # ID unique par run via timestamp → Reeder traite chaque digest comme nouveau.
    fe.id(f"{DIGEST_URL}#{now.strftime('%Y%m%d-%H%M')}")
    fe.title(f"Digest — {now.strftime('%d/%m %Hh')}")
    fe.link(href=DIGEST_URL)
    fe.pubDate(now)
    # description = fallback texte ; content:encoded = HTML rendu par Reeder.
    # On pousse le Markdown brut dans description au cas où un client RSS ne
    # supporterait pas content:encoded.
    fe.description(content_md)
    fe.content(md_to_html(content_md), type="CDATA")

    Path("output").mkdir(exist_ok=True)
    fg.rss_file(OUTPUT_FILE, pretty=True)

def md_to_html(md: str) -> str:
    """Conversion Markdown → HTML minimale, sans dépendance externe.

    Couvre uniquement ce que les prompts produisent : ## titres, **gras**,
    [liens](url), et listes à puces `- `. Si le format des prompts évolue
    (tableaux, citations…), il faudra étendre cette fonction OU passer
    sur `markdown` ou `mistune` (ajoute une dépendance).
    """
    html = md
    html = re.sub(r"## (.+)", r"<h2>\1</h2>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)

    # Conversion des listes à puces : on gère l'ouverture/fermeture du <ul>
    # en suivant l'état `in_list` ligne par ligne.
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
        out.append("</ul>")  # ferme le <ul> si la liste finit le document
    return "\n".join(out)

# ---- Main --------------------------------------------------------------------

def main():
    """Orchestration : charge → fetch → score → synthèse → écrit RSS + seen.

    Sortie anticipée si rien à traiter (économise les appels API). Dans tous
    les cas où on a appelé Haiku, on persiste seen.json même si zéro article
    n'est retenu — sinon ces articles seraient re-scorés au run suivant.
    """
    print(f"=== Digest run {datetime.now().isoformat()} ===")

    sources = load_sources(OPML_FILE)
    print(f"Sources chargées : {len(sources)}")

    seen = load_seen()
    articles = fetch_recent_articles(sources, seen)
    print(f"Articles frais trouvés : {len(articles)}")

    if not articles:
        # Cas typique : nuit, week-end, ou cron qui rejoue trop tôt.
        print("Rien de neuf, on sort.")
        return

    # Étape de scoring : on marque seen[hash] DÈS l'appel Haiku, indépendamment
    # du score retenu — un article scoré 1 ne doit pas être rescore au run suivant.
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
        # On sauvegarde quand même seen.json pour ne pas re-scorer ces articles.
        save_seen(seen)
        print("Rien de pertinent, on sort.")
        return

    # Regroupement par catégorie OPML, puis tri par score décroissant
    # et cap à MAX_ARTICLES_PER_CATEGORY (filet de sécurité coût Sonnet).
    by_cat = defaultdict(list)
    for a in scored:
        by_cat[a["category"]].append(a)
    for cat in by_cat:
        by_cat[cat] = sorted(by_cat[cat], key=lambda x: -x["score"])[:MAX_ARTICLES_PER_CATEGORY]

    # Synthèse : un appel Sonnet par catégorie (séquentiel, ~3-5 appels par run).
    sections = {}
    for cat, items in by_cat.items():
        print(f"  synthèse {cat} ({len(items)} articles)")
        sections[cat] = synthesize(cat, items)

    # Persistance finale : RSS d'abord, puis seen (cohérence de l'état si crash).
    write_rss(sections)
    save_seen(seen)
    print(f"✓ Digest écrit dans {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
