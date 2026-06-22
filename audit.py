"""Audit du pipeline : trois logs Markdown persistés sous logs/.

Trois fichiers, tous append en bas, rétention glissante 30 jours :

- logs/audit-details.md : un tableau par run, articles score >= 3 uniquement.
- logs/audit-summary.md : une ligne par run, compteurs agrégés.
- logs/audit-errors.md  : un tableau plat, une ligne par erreur survenue.

Les erreurs sont collectées au fil du run via record_error(). À la fin du run,
digest.py appelle log_run() qui écrit les trois fichiers et purge l'historique
au-delà de RETENTION_DAYS.

Cross-link : la colonne `Err` du summary pointe vers audit-errors.md (sans ancre
précise — la table reste plate côté errors). Pour retrouver les erreurs d'un run
donné, ouvrir audit-errors.md et Cmd+F la date.
"""

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_DIR = Path("logs")
DETAILS_FILE = LOG_DIR / "audit-details.md"
SUMMARY_FILE = LOG_DIR / "audit-summary.md"
ERRORS_FILE = LOG_DIR / "audit-errors.md"

RETENTION_DAYS = 30

# Collecteur d'erreurs centralisé. Réinitialisé à chaque process Python
# (en pratique : un run = un process, pas besoin de reset explicite).
_errors: list[dict] = []


def record_error(phase: str, target: str, exc: Exception) -> None:
    """Enregistre une erreur pour inclusion dans audit-errors.md à la fin du run.

    Émet aussi un print sur stderr pour visibilité immédiate dans les logs
    GitHub Actions (le fichier d'audit sert au journal persistant, le stderr
    au debugging à chaud).

    Args:
        phase: "fetch", "scoring", "dedup" ou "synthese".
        target: cible humainement parlante (nom de feed, titre+source, catégorie).
        exc: l'exception à logger.
    """
    msg = _explain_error(exc)
    _errors.append({
        "ts": datetime.now(timezone.utc),
        "phase": phase,
        "target": target,
        "message": msg,
    })
    print(f"  ! [{phase}] {target}: {msg}", file=sys.stderr)


def log_run(
    run_ts: datetime,
    articles_scored: list[dict],
    metrics: dict,
) -> None:
    """Écrit les trois fichiers d'audit et purge l'historique > 30 jours.

    Args:
        run_ts: timestamp du début du run (UTC).
        articles_scored: tous les articles passés en phase 1 avec leur dict de
            scoring (clés attendues : score_phase1, decision, tag, raison,
            title, source, link).
        metrics: dict avec les clés trouves, read_now, read_later, archive,
            doublons, filtering_model, synthesis_model.
    """
    LOG_DIR.mkdir(exist_ok=True)
    _write_details(run_ts, articles_scored)
    _write_summary(run_ts, metrics)
    _write_errors(run_ts)
    _purge_old_runs(DETAILS_FILE, _details_block_pattern())
    _purge_old_runs(SUMMARY_FILE, _summary_line_pattern())
    _purge_old_runs(ERRORS_FILE, _errors_line_pattern())


# ---- Détails (log 1) --------------------------------------------------------

def _write_details(run_ts: datetime, articles_scored: list[dict]) -> None:
    """Append un bloc `## Run …` avec TOUS les articles scorés en phase 1.

    Tri intra-run : par score_phase1 décroissant. Plafonds abrégés. La
    colonne Décision reflète l'état final (post-dédup), donc un article
    rétrogradé en doublon apparaît avec Décision=archive et Raison="doublon
    de [N] …".

    On trace tous les articles (et plus seulement score >= 3) : c'est
    précisément le détail des articles rejetés qui permet de comprendre
    pourquoi un run ne retient rien. Une ligne de distribution résume les
    scores en tête de bloc.
    """
    keepers = list(articles_scored)
    keepers.sort(key=lambda a: -a.get("score_phase1", 0))

    block = [f"\n## Run {_fmt_ts(run_ts)}\n"]
    if not keepers:
        block.append("\n_Aucun article scoré sur ce run._\n")
    else:
        block.append(f"\n{_score_distribution(keepers)}\n")
        block.append(
            "\n| Sc | Décision | Tag | Titre | Source | Raison |\n"
            "|---:|---|---|---|---|---|\n"
        )
        for a in keepers:
            title_md = f"[{_escape_md_cell(a.get('title', ''))}]({a.get('link', '')})"
            block.append(
                "| {sc} | {dec} | {tag} | {title} | {src} | {raison} |\n".format(
                    sc=a.get("score_phase1", 0),
                    dec=a.get("decision", ""),
                    tag=a.get("tag", ""),
                    title=title_md,
                    src=_escape_md_cell(a.get("source", "")),
                    raison=_escape_md_cell(a.get("raison", "")),
                )
            )
    _append(DETAILS_FILE, "".join(block), header=_details_header())


def _details_header() -> str:
    return (
        "# Audit détaillé — 30 derniers jours\n"
        "\n"
        "Rétention glissante 30 jours. Append en bas. Stocke TOUS les articles scorés\n"
        "en phase 1 (y compris rejetés) pour pouvoir diagnostiquer un run sans rétention.\n"
        "Tri intra-run par score décroissant. Chaque bloc commence par la distribution\n"
        "des scores. La colonne Décision reflète l'état final post-dédup.\n"
    )


def _score_distribution(articles: list[dict]) -> str:
    """Ligne récap des scores phase 1, ex: `Distribution : 5×s1, 3×s2, 1×s3`."""
    counts: dict[int, int] = {}
    for a in articles:
        s = a.get("score_phase1", 0)
        counts[s] = counts.get(s, 0) + 1
    parts = [f"{counts[s]}×s{s}" for s in sorted(counts, reverse=True)]
    return "Distribution : " + ", ".join(parts)


def _details_block_pattern() -> re.Pattern:
    return re.compile(r"^## Run (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC\s*$")


# ---- Summary (log 2) --------------------------------------------------------

def _write_summary(run_ts: datetime, metrics: dict) -> None:
    """Append une ligne au tableau summary.

    Si une ligne d'en-tête de tableau n'existe pas encore, on l'écrit. Sinon
    on append juste la ligne de données.
    """
    trouves = metrics.get("trouves", 0)
    rn = metrics.get("read_now", 0)
    rl = metrics.get("read_later", 0)
    skim = metrics.get("skim", 0)
    archive = metrics.get("archive", 0)
    doublons = metrics.get("doublons", 0)
    n_err = len(_errors)
    # Retenue = part des articles qui entrent dans le digest (RN + RL + skim,
    # cf. ACCEPTED_DECISIONS). skim est retenu depuis 2026-06-22.
    retenue = f"{round(100 * (rn + rl + skim) / trouves)}%" if trouves else "—"

    # Cross-link vers audit-errors.md si erreur(s)
    err_cell = f"[{n_err}](audit-errors.md)" if n_err else "0"

    # Modèles abrégés
    filt = _abbreviate_model(metrics.get("filtering_model", ""))
    synth = _abbreviate_model(metrics.get("synthesis_model", ""))

    line = (
        f"| {_fmt_ts(run_ts)} | {filt} | {synth} | "
        f"{trouves} | {rn} | {rl} | {skim} | {archive} | {doublons} | {err_cell} | {retenue} |\n"
    )

    _append_summary_line(SUMMARY_FILE, line)


def _summary_header() -> str:
    return (
        "# Synthèse pipeline — 30 derniers jours\n"
        "\n"
        "Rétention glissante 30 jours. Append en bas (le plus récent en bas).\n"
        "\n"
        "- `Trouvés` : articles frais après filtrage URL/date.\n"
        "- `RN` / `RL` / `Skim` : retenus en read_now / read_later / skim (entrent dans le digest).\n"
        "- `Arch` : non retenu (decision = archive).\n"
        "- `Dédup` : articles rétrogradés par la phase 2.\n"
        "- `Err` : erreurs survenues (cliquable → audit-errors.md).\n"
        "- `Retenue%` : (RN + RL + Skim) / Trouvés.\n"
        "\n"
        "| Date UTC | Filtrage | Synthèse | Trouvés | RN | RL | Skim | Arch | Dédup | Err | Retenue% |\n"
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )


def _summary_line_pattern() -> re.Pattern:
    # Une ligne summary commence par "| 2026-06-19 18:01 |"
    return re.compile(r"^\| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \|")


def _append_summary_line(filepath: Path, line: str) -> None:
    """Append spécifique au summary : on n'a pas de ## bloc, juste l'en-tête puis des lignes."""
    if not filepath.exists():
        filepath.write_text(_summary_header() + line, encoding="utf-8")
        return
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line)


# ---- Errors (log 3) ---------------------------------------------------------

def _write_errors(run_ts: datetime) -> None:
    """Append les lignes d'erreur collectées via record_error() pendant ce run.

    Si _errors est vide, on n'ajoute aucune ligne (silence = bonne nouvelle)
    mais on garantit que le fichier existe avec son en-tête, pour que les trois
    logs soient toujours présents sous logs/ (besoin : 3 logs persistés).
    """
    if not _errors:
        if not ERRORS_FILE.exists():
            ERRORS_FILE.write_text(_errors_header(), encoding="utf-8")
        return
    block = []
    for err in _errors:
        block.append(
            f"| {_fmt_ts(err['ts'])} | {err['phase']} | "
            f"{_escape_md_cell(err['target'])} | {_escape_md_cell(err['message'])} |\n"
        )
    _append_errors_lines(ERRORS_FILE, "".join(block))


def _errors_header() -> str:
    return (
        "# Audit erreurs — 30 derniers jours\n"
        "\n"
        "Rétention glissante 30 jours. Append en bas. Aucune ligne pour un run\n"
        "donné == pipeline sain. Phases : `fetch` (feed RSS), `scoring` (phase 1),\n"
        "`dedup` (phase 2), `synthese` (phase 3).\n"
        "\n"
        "| Date UTC | Phase | Cible | Erreur |\n"
        "|---|---|---|---|\n"
    )


def _errors_line_pattern() -> re.Pattern:
    return re.compile(r"^\| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \|")


def _append_errors_lines(filepath: Path, content: str) -> None:
    if not filepath.exists():
        filepath.write_text(_errors_header() + content, encoding="utf-8")
        return
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(content)


# ---- Purge ------------------------------------------------------------------

def _purge_old_runs(filepath: Path, header_pattern: re.Pattern) -> None:
    """Supprime du fichier toutes les entrées dont le timestamp est > 30 jours.

    Pour le fichier `details` : un bloc = `## Run YYYY-MM-DD HH:MM UTC` suivi
    de son contenu jusqu'au prochain bloc.
    Pour `summary` et `errors` : une ligne = une entrée, le timestamp est dans
    la première colonne du tableau.

    On préserve les lignes qui ne matchent pas le pattern (en-tête, paragraphes
    explicatifs, en-tête de tableau).
    """
    if not filepath.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)

    kept: list[str] = []
    skip_block = False
    for line in lines:
        match = header_pattern.match(line)
        if match:
            # On entre dans une nouvelle entrée. On regarde sa date.
            ts = _parse_ts(match.group(1))
            if ts and ts < cutoff:
                # Trop vieille : on saute jusqu'à la prochaine entrée
                # (vrai uniquement pour les `## Run …` du fichier details ;
                #  pour summary/errors une ligne = une entrée, donc on saute
                #  juste cette ligne).
                skip_block = True
                continue
            skip_block = False
            kept.append(line)
            continue
        if skip_block:
            # On reste dans le bloc à supprimer jusqu'au prochain `## Run`
            continue
        kept.append(line)

    filepath.write_text("".join(kept), encoding="utf-8")


# ---- Helpers ----------------------------------------------------------------

def _fmt_ts(dt: datetime) -> str:
    """Format ISO compact sans secondes, en UTC."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _parse_ts(s: str) -> datetime | None:
    """Parse une chaîne `2026-06-19 18:01` en datetime UTC."""
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _abbreviate_model(slug: str) -> str:
    """Abrège un slug de modèle pour le tableau summary.

    Stratégie : derniers tokens du slug, séparés par `-`. On vise une
    chaîne courte (≤ 20 chars) mais reconnaissable.

    Exemples :
    - openrouter/deepseek/deepseek-v4-flash → dsv4-flash
    - anthropic/claude-haiku-4-5-20251001  → claude-haiku-4-5
    - openrouter/openai/gpt-5-mini         → gpt-5-mini
    """
    if not slug:
        return "—"
    name = slug.rsplit("/", 1)[-1]
    # Cas particulier deepseek : "deepseek-v4-flash" → "dsv4-flash"
    if name.startswith("deepseek-"):
        name = "ds" + name[len("deepseek-"):]
    # Tronquer dates de version "claude-haiku-4-5-20251001" → enlever le dernier
    # segment s'il ressemble à une date.
    parts = name.split("-")
    if parts and re.fullmatch(r"\d{6,}", parts[-1]):
        parts = parts[:-1]
    return "-".join(parts)


def _explain_error(exc: Exception) -> str:
    """Traduit l'exception en message lisible pour le log d'erreurs.

    Évite la stack trace brute. Pour les cas connus, message explicite.
    Pour le reste, ClassName + message tronqué à 150 chars.
    """
    msg = str(exc)
    name = type(exc).__name__
    if "'NoneType' object has no attribute 'strip'" in msg:
        return "content=None côté LLM (modèle a refusé ou renvoyé vide)"
    if name == "JSONDecodeError":
        return f"JSON malformé renvoyé par le LLM ({msg[:80]})"
    if "RateLimit" in name:
        return "Rate limit fournisseur LLM atteint"
    if "Timeout" in name:
        return "Timeout fournisseur LLM"
    if "Authentication" in name or "Unauthorized" in name:
        return "Clé API invalide ou expirée"
    if "BadRequest" in name:
        return f"Requête refusée par le LLM ({msg[:80]})"
    if "Connection" in name:
        return f"Erreur réseau ({msg[:80]})"
    return f"{name}: {msg}"[:150]


def _escape_md_cell(text: str) -> str:
    """Échappe pour utilisation dans une cellule de tableau Markdown."""
    if not text:
        return ""
    # | casse la structure de table, on l'échappe.
    # Les newlines doivent disparaître sinon GitHub coupe le tableau.
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", "").strip()


# ---- Append helpers ---------------------------------------------------------

def _append(filepath: Path, content: str, header: str) -> None:
    """Append générique pour le fichier details (bloc `## Run …`)."""
    if not filepath.exists():
        filepath.write_text(header + content, encoding="utf-8")
        return
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(content)
