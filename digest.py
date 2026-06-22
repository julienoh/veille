"""Pipeline de curation RSS : OPML → fetch → filtrage (2 phases) → synthèse → RSS.

Vue d'ensemble du flux (un run = une exécution déclenchée par GitHub Actions) :

    1. load_sources()           Lit sources.opml et retourne la liste des feeds
    2. fetch_recent_articles()  feedparser sur chaque feed, filtre par date
                                (LOOKBACK_HOURS) et déduplication via seen.json
    3. score_article()          Phase 1 : un appel LLM de filtrage par article
                                → JSON enrichi (score, decision, tag, confiance…)
    4. deduplicate_category()   Phase 2 : un appel LLM de filtrage par catégorie
                                → rétrograde les doublons en decision=archive
    5. synthesize()             Appel LLM de synthèse par catégorie OPML
                                → Markdown éditorial
    6. write_rss()              Génère output/digest.xml (1 item RSS contenant
                                toutes les sections concaténées)
    7. save_seen()              Persiste seen.json avec rétention SEEN_RETENTION_DAYS

Effets de bord persistés (commités dans le repo par le workflow Actions) :
- output/digest.xml  : le flux servi par GitHub Pages
- seen.json          : dictionnaire {hash: date_iso} des articles déjà traités

Tous les paramètres ajustables sont regroupés dans la section Configuration ci-dessous.
Les prompts LLM vivent dans prompt.py pour pouvoir itérer dessus indépendamment
du code (historique git séparé).
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
from feedgen.feed import FeedGenerator

import audit
from llm_client import complete
from prompt import SCORING_PROMPT, DEDUP_PROMPT, SYNTHESIS_PROMPT

# ---- Configuration -----------------------------------------------------------
# Tous les paramètres ajustables du pipeline sont regroupés ici.
# Voir README.md §5 "Paramètres de tuning" pour la sémantique de chacun.

# Chemins (relatifs au cwd, qui est la racine du repo en CI comme en local)
OPML_FILE = "sources.opml"           # Source de vérité des feeds
SEEN_FILE = "seen.json"              # Dédoublonnage persistant {hash: iso_date}
OUTPUT_FILE = "output/digest.xml"    # Flux RSS généré, servi par GitHub Pages
DIGEST_URL = "https://julienoh.github.io/veille/digest.xml"  # URL publique du flux

# Comportement du pipeline
LOOKBACK_HOURS = 8                 # Fenêtre temporelle des articles à considérer.
                                   # Les 3 runs/jour (8h d'écart) se recouvrent
                                   # légèrement → pas de trou en cas de retard cron.
ACCEPTED_DECISIONS = {"read_now", "read_later", "skim"}  # Décisions qui passent dans le digest.
                                                         # Seul "archive" est écarté.
                                                         # Avec le mapping du SCORING_PROMPT
                                                         # (5→read_now, 4→read_later, 3→skim),
                                                         # cela revient à retenir tout score >= 3.
MAX_ARTICLES_PER_CATEGORY = 20     # Garde-fou contre les pics de volume (ex: arXiv)
                                   # qui exploseraient la facture du LLM de synthèse.
SEEN_RETENTION_DAYS = 14           # Fenêtre de déduplication. Au-delà, l'entrée
                                   # est purgée → un article peut réapparaître après.

# LLMs utilisés. Le nom porte le provider en préfixe (cf. llm_client.py).
# Provider "anthropic/" → SDK Anthropic direct (clé ANTHROPIC_API_KEY).
# Provider "openrouter/" → SDK OpenAI sur https://openrouter.ai/api/v1 (clé OPENROUTER_API_KEY).
# On peut mixer les deux providers entre phase de filtrage et phase de synthèse.
FILTERING_MODEL = "openrouter/deepseek/deepseek-v4-flash"  # Phases 1 et 2 (scoring + dédup)
SYNTHESIS_MODEL = "openrouter/deepseek/deepseek-v4-pro"    # Phase 3 (synthèse éditoriale)

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
# (avec [skip ci] pour éviter une boucle de déclenchement).

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
            audit.record_error("fetch", src["title"], e)
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
            # Limité à 800 chars car (a) on n'envoie que 400 au LLM de filtrage,
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

# ---- Phase 1 : scoring article par article -----------------------------------

def score_article(article: dict) -> dict | None:
    """Phase 1 : note un article via le LLM de filtrage.

    Le prompt impose un JSON compact : score, decision, tags (liste 1-3), raison.
    En pratique le modèle ajoute parfois du texte autour — on extrait le premier
    objet JSON via regex.

    Returns:
        Dict complet du scoring, ou None si l'appel/parse échoue.
        None est traité par le caller comme "pas retenu" (ne casse pas le run).
    """
    try:
        text = complete(
            model=FILTERING_MODEL,
            max_tokens=400,  # JSON enrichi mais court → cap large mais raisonnable
            prompt=SCORING_PROMPT.format(
                title=article["title"],
                source=article["source"],
                # 400 chars suffisent pour décider de la pertinence,
                # et limitent la facture LLM sur 50 articles × 3 runs/j.
                summary=article["summary"][:400],
            ),
        )
        # Extraction du premier objet JSON présent dans la réponse.
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group(0))
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        return {
            "score": int(data["score"]),
            "decision": data.get("decision", "archive"),
            # Le prompt renvoie une liste `tags` (1-3). On garde le premier comme
            # tag principal (groupement/affichage), le reste en secondaires.
            "tag": tags[0] if tags else "autre",
            "tags_secondaires": tags[1:3],
            "raison": data.get("raison", ""),
        }
    except Exception as e:
        # On loggue mais on n'échoue pas le run pour un seul article.
        target = f"{article.get('title', '')[:60]} ({article.get('source', '')})"
        audit.record_error("scoring", target, e)
        return None

# ---- Phase 2 : déduplication par catégorie OPML ------------------------------

def deduplicate_category(category: str, articles: list[dict]) -> list[dict]:
    """Phase 2 : élimine les doublons sémantiques au sein d'une catégorie.

    Un seul appel LLM par catégorie : on lui envoie tous les articles 3-5
    de la catégorie, il retourne des clusters de doublons. Pour chaque cluster,
    les articles non-canoniques sont rétrogradés en decision=archive et score=2.

    Args:
        category: nom de la catégorie OPML.
        articles: liste d'articles déjà filtrés (decision in ACCEPTED_DECISIONS).

    Returns:
        Liste filtrée : articles uniques + canoniques retenus pour la synthèse.
    """
    if len(articles) < 2:
        # Aucun doublon possible.
        return articles

    # Format compact indexé pour le LLM. 200 chars de résumé suffisent
    # pour décider si deux articles parlent du même sujet.
    articles_txt = "\n".join(
        f"[{i}] {a['title']} | {a['source']} | {a['summary'][:200]}"
        for i, a in enumerate(articles)
    )

    try:
        text = complete(
            model=FILTERING_MODEL,
            max_tokens=800,  # Liste de clusters, format compact
            prompt=DEDUP_PROMPT.format(
                category=category,
                articles=articles_txt,
            ),
        )
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return articles
        data = json.loads(m.group(0))
    except Exception as e:
        # Une erreur de dédup ne doit pas faire planter le run : on garde tout.
        audit.record_error("dedup", category, e)
        return articles

    groupes = data.get("groupes", [])
    n_demoted = 0
    for g in groupes:
        canonical = g.get("canonical_id")
        sujet = g.get("sujet", "")
        for idx in g.get("ids", []):
            # Sécurité : index hors borne ou canonique → on ne touche pas.
            if idx == canonical or not (0 <= idx < len(articles)):
                continue
            articles[idx]["decision"] = "archive"
            articles[idx]["score"] = 2
            articles[idx]["raison"] = f"doublon de [{canonical}] {sujet}"[:120]
            n_demoted += 1

    if n_demoted:
        print(f"    dédup {category} : {n_demoted} doublon(s) rétrogradé(s)")

    # Filtre final : on ne garde que ce qui passe encore la décision attendue.
    return [a for a in articles if a.get("decision") in ACCEPTED_DECISIONS]

# ---- Phase 3 : synthèse éditoriale --------------------------------------------

def synthesize(category: str, articles: list[dict]) -> str:
    """Demande au LLM de synthèse un Markdown éditorial pour une catégorie.

    Un appel par catégorie OPML (vs un appel global) → meilleur regroupement
    thématique et permet d'ajuster le ton par catégorie si besoin via le prompt.

    Une erreur du LLM de synthèse est isolée : on log via audit et on renvoie
    "" — le caller filtre les sections vides pour ne pas écrire une catégorie
    cassée dans le RSS. Les autres catégories continuent.

    Args:
        category: nom de la catégorie OPML (ex: "Sources françaises IA")
        articles: liste d'articles déjà filtrés et dédupliqués, triés par score
            décroissant.

    Returns:
        Markdown brut, ou "" en cas d'erreur (à filtrer côté caller).
    """
    # Format compact lisible pour le modèle. 300 chars de résumé suffisent
    # ici car le LLM de synthèse n'a pas besoin de tout le contenu.
    articles_txt = "\n\n".join(
        f"- Titre : {a['title']}\n  Source : {a['source']} ({a['link']})\n"
        f"  Résumé : {a['summary'][:300]}"
        for a in articles
    )
    try:
        return complete(
            model=SYNTHESIS_MODEL,
            max_tokens=2000,  # ~3-4 paragraphes Markdown, large marge
            prompt=SYNTHESIS_PROMPT.format(
                category=category,
                period=f"dernières {LOOKBACK_HOURS}h",
                articles=articles_txt,
            ),
        )
    except Exception as e:
        audit.record_error("synthese", category, e)
        return ""

# ---- Génération du flux RSS --------------------------------------------------

def write_rss(sections: dict[str, str]) -> None:
    """Génère output/digest.xml avec UN SEUL item contenant tout le digest.

    Choix éditorial : on veut un format "bulletin" — Reeder affiche
    "1 nouveau bulletin" 3x/jour, plutôt qu'une liste de N items
    atomiques à marquer lus un par un.

    Args:
        sections: {nom_catégorie: markdown_synthèse} produit par synthesize()
    """
    fg = FeedGenerator()
    fg.id(DIGEST_URL)
    fg.title("Veille IA & Cyber — Digest perso")
    fg.link(href=DIGEST_URL, rel="self")
    fg.description("Digest IA et cybersécurité généré par LLM")
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
    """Orchestration : charge → fetch → phase 1 → phase 2 → synthèse → RSS + audit.

    Sortie anticipée si rien à traiter (économise les appels LLM). Dans tous
    les cas où on a appelé la phase 1, on persiste seen.json même si zéro article
    n'est retenu — sinon ces articles seraient re-scorés au run suivant.

    À la fin du run (succès ou sortie anticipée), audit.log_run() est appelé pour
    écrire les trois fichiers d'audit Markdown sous logs/.
    """
    run_ts = datetime.now(timezone.utc)
    print(f"=== Digest run {run_ts.isoformat()} ===")

    base_metrics = {
        "filtering_model": FILTERING_MODEL,
        "synthesis_model": SYNTHESIS_MODEL,
    }

    sources = load_sources(OPML_FILE)
    print(f"Sources chargées : {len(sources)}")

    seen = load_seen()
    articles = fetch_recent_articles(sources, seen)
    n_trouves = len(articles)
    print(f"Articles frais trouvés : {n_trouves}")

    if not articles:
        # Cas typique : nuit, week-end, ou cron qui rejoue trop tôt.
        audit.log_run(run_ts, [], {
            **base_metrics, "trouves": 0, "read_now": 0, "read_later": 0,
            "archive": 0, "doublons": 0,
        })
        print("Rien de neuf, on sort.")
        return

    # --- Phase 1 : scoring article par article -------------------------------
    # On marque seen[hash] DÈS l'appel LLM, indépendamment du score retenu —
    # un article scoré 1 ne doit pas être re-scoré au run suivant.
    # all_scored contient TOUS les articles qui ont eu un scoring réussi (pour
    # le log d'audit). pipeline ne contient que ceux qui passent ACCEPTED_DECISIONS.
    print(f"Phase 1 : scoring ({n_trouves} articles)")
    all_scored: list[dict] = []
    pipeline: list[dict] = []
    for i, a in enumerate(articles):
        if i % 20 == 0 and i > 0:
            print(f"  scoring {i}/{n_trouves}")
        result = score_article(a)
        seen[a["hash"]] = datetime.now(timezone.utc).isoformat()
        if result:
            a.update(result)
            # Snapshot du score avant que la phase 2 puisse le rétrograder à 2.
            # Permet au log d'audit de tracer la décision phase 1 initiale.
            a["score_phase1"] = a["score"]
            all_scored.append(a)
            if a["decision"] in ACCEPTED_DECISIONS:
                pipeline.append(a)

    print(f"Phase 1 terminée : {len(pipeline)} articles retenus "
          f"(decision ∈ {sorted(ACCEPTED_DECISIONS)})")

    if not pipeline:
        # On sauvegarde quand même seen.json pour ne pas re-scorer ces articles.
        save_seen(seen)
        audit.log_run(run_ts, all_scored, {
            **base_metrics, "trouves": n_trouves, "read_now": 0, "read_later": 0,
            "archive": n_trouves, "doublons": 0,
        })
        print("Rien de pertinent, on sort.")
        return

    # --- Regroupement par catégorie OPML -------------------------------------
    by_cat = defaultdict(list)
    for a in pipeline:
        by_cat[a["category"]].append(a)

    # --- Phase 2 : déduplication par catégorie -------------------------------
    print(f"Phase 2 : déduplication ({len(by_cat)} catégories)")
    n_before_dedup = len(pipeline)
    for cat in list(by_cat.keys()):
        by_cat[cat] = deduplicate_category(cat, by_cat[cat])
        # Tri par score décroissant et cap MAX_ARTICLES_PER_CATEGORY
        # (filet de sécurité coût LLM de synthèse).
        by_cat[cat] = sorted(by_cat[cat], key=lambda x: -x["score"])[:MAX_ARTICLES_PER_CATEGORY]

    # Une catégorie peut être devenue vide après dédup → on la retire.
    by_cat = {k: v for k, v in by_cat.items() if v}
    n_after_dedup = sum(len(v) for v in by_cat.values())
    n_doublons = n_before_dedup - n_after_dedup
    print(f"Phase 2 terminée : {n_after_dedup} articles après dédup "
          f"({n_doublons} rétrogradé(s))")

    # Recompte final basé sur all_scored (modifié en place par dedup_category).
    n_rn = sum(1 for a in all_scored if a.get("decision") == "read_now")
    n_rl = sum(1 for a in all_scored if a.get("decision") == "read_later")
    metrics = {
        **base_metrics,
        "trouves": n_trouves,
        "read_now": n_rn,
        "read_later": n_rl,
        "archive": n_trouves - n_rn - n_rl,
        "doublons": n_doublons,
    }

    if not by_cat:
        save_seen(seen)
        audit.log_run(run_ts, all_scored, metrics)
        print("Tout est doublon, on sort.")
        return

    # --- Phase 3 : synthèse éditoriale ---------------------------------------
    # Une catégorie qui plante en synthèse retourne "" → on la skip dans le RSS.
    # Les autres catégories continuent. Si tout plante, on n'écrit pas le RSS.
    print(f"Phase 3 : synthèse ({len(by_cat)} catégories)")
    sections = {}
    for cat, items in by_cat.items():
        print(f"  synthèse {cat} ({len(items)} articles)")
        result = synthesize(cat, items)
        if result:
            sections[cat] = result

    if sections:
        write_rss(sections)
        print(f"✓ Digest écrit dans {OUTPUT_FILE}")
    else:
        print("! Toutes les synthèses ont échoué — RSS non mis à jour pour ce run.")

    save_seen(seen)
    audit.log_run(run_ts, all_scored, metrics)

if __name__ == "__main__":
    main()
