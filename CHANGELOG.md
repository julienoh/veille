# Changelog

Tous les changements notables du projet sont documentés ici.

Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).
Le projet suit un versionnement informel (pas de tags pour l'instant).

## [Non publié]

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
