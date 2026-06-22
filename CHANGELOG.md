# Changelog

Tous les changements notables du projet sont documentés ici.

Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).
Le projet suit un versionnement informel (pas de tags pour l'instant).

## [Non publié]

### Changed
- **2026-06-22** — `SCORING_PROMPT` simplifié pour maximiser le rappel (« on
  loupe trop d'articles ») :
  - Schéma de sortie réduit à `{score, decision, tags, raison}` (abandon de
    `confiance`, `signal_principal`, `plafond_appliqué`, et `tag`+`tags_secondaires`
    fusionnés en une liste `tags` de 1-3).
  - **Décision strictement déterministe sans exception** : 5→read_now,
    4→read_later, 3→skim, 2/1→archive. Rétention = score ≥ 3.
  - **Suppression de tous les plafonds** (recall max, bruit marketing assumé).
  - Recherche IA théorique sortie du score 2 (peut atteindre 3 = retenu).
  - `digest.py` parse `tags` (1ᵉʳ = principal, reste = secondaires) ; `audit.py`
    perd les colonnes Conf/Signal/Plafond (devenues constantes) + code mort retiré.
- **2026-06-22** — Refonte du `SCORING_PROMPT` pour le rendre déterministe :
  - **Règle d'agrégation explicite** : 4 axes notés sur {0,1,2} (Actionabilité,
    Fiabilité, Nouveauté, Profondeur), score brut = `2 + A` avec A=0 ⇒ score ≤ 2,
    F=0 ⇒ score = 2, élévation à 5 réservée aux signaux forts vérifiables. Les
    anciennes bandes deviennent des exemples de calibration.
  - **Mapping score→décision déterministe** (5→read_now, 4→read_later, 3→skim,
    2/1→archive) avec exceptions strictes chiffrées (A=2, P≥1, urgence explicite).
  - Deux nouveaux tags **définis** : `ia_stratégie`, `ia_management_equipe` (+
    ordre de précédence des tags). `confiance` et `signal_principal` outillés.
- **2026-06-22** — `ACCEPTED_DECISIONS` inclut désormais `"skim"` →
  `{read_now, read_later, skim}`, ce qui revient à retenir tout score ≥ 3
  (avant : score 4-5 seulement, rétention ~0 % les jours calmes).

### Fixed
- **2026-06-22** — Métriques d'audit : depuis l'ajout de `skim` à
  `ACCEPTED_DECISIONS`, les articles `skim` (retenus dans le digest) étaient
  comptés dans `Arch` et exclus de `Retenue%` → rétention sous-estimée (17 %
  affiché vs 31 % réel). Ajout d'un compteur `skim`, d'une colonne `Skim` dans
  `audit-summary.md`, et `Retenue% = (RN + RL + Skim) / Trouvés`.
- **2026-06-22** — `llm_client` : `resp.choices[0]` levait `TypeError: 'NoneType'
  object is not subscriptable` quand OpenRouter renvoie `choices` vide/None
  (réponse d'erreur/refus) → article perdu au scoring. Garde ajoutée (retourne
  "" comme pour `content=None`).
- **2026-06-22** — Bloquant d'exécution dans la refonte du `SCORING_PROMPT` :
  accolades du schéma JSON non échappées → `KeyError` à chaque `.format()`
  (digest vide permanent). Toutes les accolades littérales doublées (`{{ }}`).
- **2026-06-22** — `llm_client.complete()` n'envoyait aucune `temperature` →
  les deux providers échantillonnaient à leur défaut (1.0), rendant le scoring
  non reproductible (un même article pouvait basculer de score d'un run à
  l'autre, bruit dans les logs d'audit). Ajout de `temperature=0` (constante
  `TEMPERATURE`) sur tous les appels. Déterminisme quasi-total — résiduel
  possible côté MoE/routage OpenRouter, atténuable via seed + provider.order.

- **2026-06-21** — Workflow `digest.yml` : collision au `git push` quand deux
  runs se chevauchaient (`! [rejected] (fetch first)`). Ajout d'un garde-fou
  `concurrency: build-digest` (cancel-in-progress=false) qui sérialise les runs,
  + `git pull --rebase --autostash` avant push en défense en profondeur.
- **2026-06-21** — Cron décalé d'1h en heure d'été : `0 6,12,18` → `0 5,11,17`
  pour viser 7h/13h/19h Paris l'été (UTC+2). 1h trop tôt l'hiver, compromis
  assumé (GitHub Actions n'a pas de support DST).
- **2026-06-21** — Audit `logs/audit-errors.md` jamais créé tant qu'aucune
  erreur ne survenait (le besoin était 3 logs persistés, seuls 2 existaient).
  Le fichier est désormais toujours écrit avec son en-tête.

### Changed
- **2026-06-21** — `logs/audit-details.md` trace désormais **tous** les articles
  scorés en phase 1 (et plus seulement score ≥ 3), avec une ligne de
  distribution des scores en tête de bloc. Motivation : un run sans rétention
  affichait `_Aucun article score ≥ 3_` et masquait les scores/raisons,
  rendant l'audit aveugle exactement quand on en avait besoin.

- **2026-04-25** — Déclencheur `push` manquant dans `.github/workflows/digest.yml`.
  Le README §3 documentait 3 déclencheurs (cron, `workflow_dispatch`, push sur
  `main`) mais le workflow n'en avait que 2. Ajout de `push: branches: [main]`
  avec `paths-ignore` sur `**.md` et `LICENSE` pour éviter un build inutile à
  chaque modification de doc.

### Changed
- **2026-04-25** — Documentation inline de `digest.py` étoffée pour
  faciliter la prise en main par un dev tiers (code inchangé,
  277 → 404 lignes) :
  - Docstring module avec vue d'ensemble des 6 étapes du pipeline
    et des effets de bord persistés
  - Section Configuration : chaque paramètre commenté avec sa
    sémantique et la justification du défaut
  - Docstrings de fonctions (Args / Returns / comportement d'erreur)
  - Commentaires aux points subtils : tolérance feed-par-feed sur les
    erreurs de fetch, extraction regex du JSON dans la réponse Haiku,
    persistance de `seen[hash]` dès l'appel Haiku indépendamment du
    score, ordre de persistance RSS puis seen pour cohérence sur crash

### À venir
- Intégration Jina Reader ou Wallabag pour fetcher le contenu complet
  des articles (feeds RSS souvent tronqués)
- Retry avec backoff sur les appels API Anthropic
- Batch scoring pour paralléliser les appels Haiku

---

## [0.1.0] — 2026-04-19

Première version fonctionnelle en production.

### Added

- Pipeline complet `digest.py` : lecture OPML → fetch RSS → déduplication
  (seen.json) → scoring Haiku → synthèse Sonnet → génération RSS
- Fichier `prompt.py` séparé avec les deux prompts (scoring + synthèse)
  pour faciliter l'itération sans toucher au code
- Workflow GitHub Actions `digest.yml` avec cron 3x/jour (7h, 13h, 19h
  heure de Paris) et déclenchement manuel (`workflow_dispatch`)
- Déploiement automatique sur GitHub Pages via branche `gh-pages`
- OPML `sources.opml` avec 53 sources organisées en 5 catégories :
  - Sources françaises IA (15)
  - Grandes sources internationales (15)
  - Labos & éditeurs (11)
  - Recherche & veille technique (7)
  - Automatisation & agents (5)
- Dédoublonnage par hash SHA1 d'URL avec fenêtre glissante de 14 jours
- Conversion Markdown → HTML artisanale pour le contenu RSS
- Documentation complète dans `README.md` (660 lignes)
- Licence MIT

### Configuration par défaut

- `LOOKBACK_HOURS = 8` (fenêtre de temps par run)
- `MIN_SCORE = 3` (seuil de pertinence Haiku)
- `MAX_ARTICLES_PER_CATEGORY = 20` (garde-fou coût API)
- `SEEN_RETENTION_DAYS = 14`
- `HAIKU_MODEL = "claude-haiku-4-5-20251001"`
- `SONNET_MODEL = "claude-sonnet-4-6"`

### Sources documentées sans RSS

Les sources suivantes sont listées dans l'OPML avec leur raison
mais n'ont pas de flux RSS exploitable :

- Bloomberg Technology (pas de RSS officiel)
- Financial Times AI (paywall)
- The Information (paywall)
- Superhuman AI (newsletter, convertir via Kill the Newsletter)
- Substack AI (agrégateur)
- Mistral AI News (pas de RSS officiel)
- Lindy Blog (pas de RSS officiel)
- Papers with Code (pas de RSS global)
- Stanford AI Index (rapports annuels uniquement)

### Feeds tiers utilisés (pas d'officiel)

- Anthropic News/Engineering via
  [Olshansk/rss-feeds](https://github.com/Olshansk/rss-feeds)
- Hugging Face Daily Papers via `papers.takara.ai`

### Fixed au cours du setup initial

- **digest.yml placé à la racine** : déplacé vers `.github/workflows/`
  pour que GitHub Actions le détecte (les dossiers cachés `.github`
  sont souvent oubliés lors d'un upload via l'interface web)
- **Erreur `Client.__init__() got an unexpected keyword argument 'proxies'`** :
  conflit de version entre `anthropic==0.39.0` (trop ancien) et `httpx`
  installé par défaut. Corrigé en passant à `anthropic>=0.49.0` et
  en ajoutant `httpx>=0.27.0` dans `requirements.txt`
- **GitHub Pages inactif après le premier run** : configuration manuelle
  nécessaire (Settings → Pages → `gh-pages` / `/ (root)`) après
  création automatique de la branche par le premier run réussi

### Notes de déploiement

- Repo public (nécessaire pour GitHub Pages gratuit)
- Minutes GitHub Actions illimitées sur repo public
- Consommation réelle observée : ~100 minutes/mois estimées (large marge)
- Clé API stockée dans GitHub Secrets (`ANTHROPIC_API_KEY`)
- Budget Anthropic plafonné à 20$/mois, auto-reload désactivé

---

## [0.0.1] — 2026-04-19

Phase de conception et construction avant première mise en production.

### Décisions d'architecture

- **Stratégie de curation choisie** : digest synthétisé par IA, 3x/jour,
  livraison par RSS sur iPhone (Reeder)
- **Stack technique retenue** : Python + GitHub Actions + GitHub Pages
  (vs VPS, Raspberry Pi, n8n, Claude Code `-p`)
- **Modèles Claude** : split Haiku (scoring) + Sonnet (synthèse)
  pour optimiser le ratio qualité/coût
- **Source de vérité des sources** : OPML standard (vs URLs hardcodées)
  pour double usage pipeline Python + import Reeder
- **Persistance** : `seen.json` commité dans le repo
  (vs SQLite éphémère sur le runner, Redis, DynamoDB)
- **Format RSS** : un item par run contenant tout le digest
  (vs un item par article)

### OPML construit

- Audit des 50 sources initiales proposées (sites francophones IA,
  grandes sources internationales, labos, recherche, automation)
- Vérification des URLs RSS via recherche web (contournement des blocages
  anti-bot qui empêchaient les tests directs)
- Identification des feeds tiers nécessaires (Anthropic, HF Daily Papers)
- Documentation des sources sans RSS (9 sur 53) avec raison explicite
- Structure hiérarchique OPML en 5 catégories pour permettre un
  scoring/synthèse différenciée par catégorie
