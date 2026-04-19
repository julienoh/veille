# Veille IA & Cyber — Digest personnel

Pipeline de curation automatique : lit des flux RSS, filtre et synthétise
avec Claude (Anthropic), expose un flux RSS consommable dans Reeder (iOS).

**URL du digest** : https://julienoh.github.io/veille/digest.xml  
**Licence** : MIT  
**Coût estimé** : ~5$/mois (API Anthropic uniquement, infra gratuite)  
**Fréquence** : 3 digests/jour (7h, 13h, 19h heure de Paris)

---

## Table des matières

1. [Pourquoi ce projet](#1-pourquoi-ce-projet)
2. [Architecture](#2-architecture)
3. [Structure du repo](#3-structure-du-repo)
4. [Sources (OPML)](#4-sources-opml)
5. [Setup complet](#5-setup-complet)
6. [Paramètres de tuning](#6-paramètres-de-tuning)
7. [Itérer sur les prompts](#7-itérer-sur-les-prompts)
8. [Coût détaillé](#8-coût-détaillé)
9. [Maintenance courante](#9-maintenance-courante)
10. [Décisions de conception](#10-décisions-de-conception)
11. [Pièges rencontrés au setup](#11-pièges-rencontrés-au-setup)
12. [Améliorations futures](#12-améliorations-futures)

---

## 1. Pourquoi ce projet

### Le besoin

Profil : Veille active sur l'IA (recherche, produits, agents)
et la cybersécurité (vulnérabilités, stratégie, gouvernance). Contrainte :
pas de temps pour scanner manuellement 50 sources plusieurs fois par jour.

### Les options évaluées

| Option | Problème |
|---|---|
| Newsletters email (TLDR AI, The Batch…) | Bon signal mais format email, fréquence imposée |
| Feedly Pro avec Leo AI | ~10€/mois, peu de contrôle sur les prompts |
| n8n workflow | Dépendance infra (VPS), UX limitée pour la logique fine |
| Claude Code en `-p` | Pas conçu pour du cron production, besoin d'une machine allumée |
| **Ce pipeline** | Contrôle total, gratuit en infra, prompts itérables |

### Les contraintes retenues

- Livraison via RSS sur iPhone (Reeder) — pas d'email, pas de Telegram
- Synthèse par IA, pas de lecture de flux bruts
- Zéro infrastructure à maintenir (GitHub Actions + Pages)
- Coût maîtrisé et prévisible (~5$/mois API)
- Pipeline versionné et reproductible (tout dans le repo)

---

## 2. Architecture

### Vue d'ensemble

```
sources.opml
    │
    ▼
digest.py  ←─── cron 3x/jour (GitHub Actions)
    │
    ├── 1. Charge les sources depuis l'OPML
    ├── 2. Fetch les flux RSS (feedparser)
    ├── 3. Filtre les articles < 8h non déjà vus (seen.json)
    ├── 4. Score chaque article avec Claude Haiku (score 1-5 + tag)
    ├── 5. Filtre les articles score >= 3
    ├── 6. Regroupe par catégorie OPML
    ├── 7. Synthétise par catégorie avec Claude Sonnet (Markdown)
    └── 8. Génère output/digest.xml (RSS)
            │
            ├──► git commit → branche main (seen.json + digest.xml)
            └──► branche gh-pages → GitHub Pages → Reeder (iOS)
```

### Flux de données détaillé

```
OPML (53 sources, 44 avec RSS)
  └─► feedparser.parse(url) — par source
        └─► filtre temporel : published > now - LOOKBACK_HOURS
              └─► filtre doublon : sha1(url)[:12] pas dans seen.json
                    └─► Claude Haiku
                          input : titre + source + résumé (400 chars max)
                          output : {"score": 1-5, "tag": "...", "raison": "..."}
                          └─► filtre : score >= MIN_SCORE
                                └─► groupement par catégorie OPML
                                      └─► Claude Sonnet (par catégorie)
                                            input : liste articles (titre, url, résumé)
                                            output : Markdown avec puces et liens
                                                  └─► feedgen → digest.xml (RSS 2.0)
                                                        └─► 1 item RSS par run
                                                              contenu : HTML converti depuis MD
```

### Choix techniques et alternatives écartées

| Choix retenu | Alternative écartée | Raison du choix |
|---|---|---|
| GitHub Actions (cron) | VPS, Raspberry Pi, n8n | Zéro infra, gratuit, logs intégrés, versionné |
| GitHub Pages | Cloudflare R2, Netlify | Même repo, zéro config supplémentaire |
| Repo public | Repo privé (payant sur Free) | GitHub Pages gratuit uniquement sur repo public |
| OPML comme source de vérité | URLs hardcodées dans le code | Portable, lisible, importable dans n'importe quel lecteur RSS |
| feedparser + feedgen | Requêtes HTTP brutes | Libs matures, gèrent les edge cases RSS/Atom |
| Haiku pour le scoring | Sonnet partout | 10x moins cher, JSON court = tâche simple |
| Sonnet pour la synthèse | Haiku, Opus | Meilleur rapport qualité/coût pour la nuance |
| seen.json commité dans git | SQLite, Redis, DynamoDB | Zéro infra, versionné, suffisant pour 14 jours |
| 1 item RSS par run | 1 item par article | Format "bulletin" plus lisible dans Reeder |
| MIT licence | Aucune licence | Ouverture maximale sans contrainte |

### Modèles utilisés

| Rôle | Modèle | Justification |
|---|---|---|
| Scoring (pertinence 1-5) | `claude-haiku-4-5-20251001` | Tâche simple, JSON court, coût minimal |
| Synthèse (Markdown par catégorie) | `claude-sonnet-4-6` | Nuance, regroupement thématique, ton éditorial |

---

## 3. Structure du repo

```
veille/
├── .github/
│   └── workflows/
│       └── digest.yml        # Workflow GitHub Actions (cron + deploy)
├── output/
│   └── digest.xml            # Flux RSS généré, commité + servi par Pages
├── digest.py                 # Script principal — pipeline complet
├── prompt.py                 # Prompts Claude isolés (à itérer indépendamment)
├── requirements.txt          # feedparser, feedgen, anthropic, httpx
├── seen.json                 # Hashes SHA1 des articles traités (fenêtre 14 jours)
├── sources.opml              # 53 sources en 5 catégories
├── LICENSE                   # MIT
└── README.md                 # Ce fichier
```

### Rôle de chaque fichier

**`digest.py`** : le pipeline complet. Contient toute la logique métier :
chargement OPML, fetch RSS, déduplication, scoring, synthèse, génération RSS.
La section `Configuration` en haut regroupe tous les paramètres ajustables.

**`prompt.py`** : les deux prompts Claude isolés dans leur propre fichier.
Ce découplage est intentionnel : on itère sur les prompts sans risquer
de casser la logique Python, et l'historique git des changements de prompts
est séparé de l'historique des changements de code.

**`sources.opml`** : la source de vérité des feeds. Le script le lit
à chaque run — modifier l'OPML suffit pour ajouter/retirer une source,
sans toucher au code. Même fichier utilisable dans Reeder pour abonnement direct.

**`seen.json`** : dictionnaire `{hash: date_iso}` des articles déjà traités.
Commité à chaque run via `git commit -m "Update digest [skip ci]"`.
La fenêtre glissante de `SEEN_RETENTION_DAYS` (14 jours) évite la croissance infinie.

**`digest.yml`** : workflow GitHub Actions. Trois déclencheurs :
cron 3x/jour, `workflow_dispatch` (bouton manuel), et push sur main.

---

## 4. Sources (OPML)

53 sources organisées en 5 catégories dans `sources.opml`.
44 ont un flux RSS actif. 9 sont documentées sans RSS (raison indiquée dans l'OPML).

### Sources françaises IA (15)

Actu IA, Usine Digitale, Frenchweb, Next.ink, Le Monde Informatique,
ZDNet France, Les Echos Tech, Maddyness, BFM Tech, Siècle Digital,
Journal du Net, UpMynt, Les Carnets de l'IA (podcast), Ria-Facile (AI Act)

### Grandes sources internationales (15)

The Batch (DeepLearning.AI), MIT Technology Review, VentureBeat AI,
TechCrunch AI, The Verge AI, Wired AI, Ars Technica, The Register,
Ben's Bites, Reuters Technology

Sans RSS libre (documentés) : Bloomberg Technology (pas de RSS officiel),
Financial Times AI (paywall), The Information (paywall), Superhuman AI
(newsletter → convertir via Kill the Newsletter), Substack AI (agrégateur)

### Labos & éditeurs (11)

OpenAI News, Google DeepMind Blog, Anthropic News (feed tiers*),
Anthropic Engineering (feed tiers*), Hugging Face Blog, NVIDIA Blog,
Microsoft AI Blog, Google AI Blog, Cohere Blog, Meta AI Blog

Sans RSS officiel : Mistral AI News

### Recherche & veille technique (7)

arXiv cs.AI (⚠ volume élevé : 200+ papiers/jour),
arXiv cs.LG (Machine Learning),
HF Daily Papers (feed tiers†),
EleutherAI Blog, LessWrong AI

Sans RSS : Papers with Code (pas de RSS global), Stanford AI Index
(rapports annuels uniquement)

### Automatisation & agents (5)

LangChain Blog, LlamaIndex Blog, n8n Blog, Relevance AI Blog

Sans RSS : Lindy Blog

### Notes sur les feeds tiers

*\* Anthropic n'a pas de RSS officiel. Les feeds utilisés sont générés
par [Olshansk/rss-feeds](https://github.com/Olshansk/rss-feeds) via
GitHub Actions toutes les heures. Fiable en pratique mais dépendant
d'un mainteneur tiers.*

*† HF Daily Papers : feed non-officiel disponible sur
`https://papers.takara.ai/api/feed`, mis à jour toutes les 24h.*

### Sources sans RSS : solution recommandée

Pour Mistral, Superhuman AI, et autres newsletters sans RSS :
utiliser [Kill the Newsletter](https://kill-the-newsletter.com) qui
convertit n'importe quelle newsletter email en flux RSS.
Ajouter l'URL générée dans `sources.opml`.

---

## 5. Setup complet

### Prérequis

- Compte GitHub gratuit
- Compte Anthropic sur [platform.claude.com](https://platform.claude.com)
  avec crédits API (20$ suffisent pour 3-4 mois)

### Étape 1 — Cloner ou forker ce repo

```bash
git clone https://github.com/julienoh/veille.git
cd veille
```

Ou forker directement sur GitHub si tu veux ta propre instance.

### Étape 2 — Adapter les sources (optionnel)

Modifier `sources.opml` pour ajouter tes propres sources ou retirer
celles qui ne t'intéressent pas. Format standard OPML, importable
dans n'importe quel lecteur RSS.

### Étape 3 — Ajuster DIGEST_URL dans digest.py

```python
# digest.py, ligne ~30
DIGEST_URL = "https://TON-USER.github.io/NOM-REPO/digest.xml"
```

### Étape 4 — Créer le repo GitHub

- Repo **public** (obligatoire pour GitHub Pages gratuit)
- Pousser tous les fichiers sur la branche `main`
- Vérifier que `.github/workflows/digest.yml` est bien présent
  (les dossiers cachés `.github` sont parfois oubliés lors d'un upload
  via l'interface web — les créer avec "Add file → Create new file"
  en tapant `.github/workflows/digest.yml` dans le nom)

### Étape 5 — Générer et configurer la clé API

1. Aller sur [platform.claude.com](https://platform.claude.com)
2. **Settings → API Keys → Create Key**
   - Nom suggéré : `veille-github-actions`
3. **Copier la clé immédiatement** (affichée une seule fois, commence par `sk-ant-api03-...`)
4. Dans le repo GitHub : **Settings → Secrets and variables → Actions →
   New repository secret**
   - Name : `ANTHROPIC_API_KEY`
   - Value : coller la clé

> ⚠️ Ne jamais mettre la clé dans le code ou dans un fichier du repo,
> même privé. GitHub Secrets est le seul endroit approprié.

### Étape 6 — Configurer les limites de dépenses

Sur [platform.claude.com](https://platform.claude.com) → **Settings → Billing → Limits** :
- Monthly budget limit : 20$ (protection contre les bugs de boucle)
- Désactiver l'auto-reload pour éviter les rechargements automatiques

### Étape 7 — Premier run manuel

Actions → **Build digest** → **Run workflow** → branche `main` → **Run workflow**

Attendre ~2 minutes. Vérifier dans les logs :
```
Sources chargées : 44
Articles frais trouvés : XX
Articles retenus (score >= 3) : XX
✓ Digest écrit dans output/digest.xml
```

Si `Articles frais trouvés : 0` : modifier temporairement
`LOOKBACK_HOURS = 48` dans `digest.py` pour un premier test,
puis remettre à 8.

### Étape 8 — Activer GitHub Pages

Après un premier run réussi (la branche `gh-pages` est créée automatiquement) :

**Settings → Pages → Source = Deploy from a branch →
Branch = `gh-pages` / `/ (root)` → Save**

Attendre 2 minutes, puis vérifier :
```
https://TON-USER.github.io/NOM-REPO/digest.xml
```
Le navigateur doit afficher du XML RSS.

### Étape 9 — Abonner Reeder (iOS)

Reeder → **+** → coller l'URL → valider.
Le flux s'appelle "Veille IA & Cyber — Digest perso".

---

## 6. Paramètres de tuning

Tous dans `digest.py`, section `Configuration` en haut du fichier.

| Paramètre | Défaut | Quand changer |
|---|---|---|
| `LOOKBACK_HOURS` | 8 | Monter à 12 si trop peu d'articles la nuit. Les 3 runs/jour se recouvrent légèrement avec 8h, ce qui évite les trous. |
| `MIN_SCORE` | 3 | Monter à 4 si trop de bruit dans le digest. Descendre à 2 si trop vide. |
| `MAX_ARTICLES_PER_CATEGORY` | 20 | Baisser à 10 si la facture API monte. Garde-fou contre les pics (ex: arXiv). |
| `SEEN_RETENTION_DAYS` | 14 | Fenêtre de déduplication. 14 jours = un article vu cette semaine ne reviendra pas la semaine prochaine. |
| `HAIKU_MODEL` | `claude-haiku-4-5-20251001` | Mettre à jour quand Anthropic sort un Haiku plus récent. |
| `SONNET_MODEL` | `claude-sonnet-4-6` | Mettre à jour quand Anthropic sort un Sonnet plus récent. |

### Grille de scoring Haiku (référence)

| Score | Signification | Exemple |
|---|---|---|
| 5 | Incontournable | Nouveau modèle majeur, CVE critique exploitée, annonce stratégique |
| 4 | Intéressant | Nouveau produit, étude de fond, benchmark important |
| 3 | Utile si du temps | Tutorial, retour d'expérience, analyse sectorielle |
| 2 | Marginal | Annonce mineure, opinion peu fondée, doublon |
| 1 | Bruit | Clickbait, promotion déguisée, hors sujet |

### Tags thématiques disponibles

`ia_recherche` · `ia_produit` · `cyber_vuln` · `cyber_strategie` ·
`dev_tooling` · `business` · `autre`

---

## 7. Itérer sur les prompts

`prompt.py` contient deux prompts. C'est là qu'on passe le plus de temps.

### SCORING_PROMPT (Haiku)

Définit le profil cible ("RSSI / DSI français passionné d'IA") et
la grille de scoring 1-5. À ajuster si :
- Des articles non pertinents passent trop souvent le filtre (affiner le profil)
- Un domaine spécifique est mal évalué (ajouter des exemples dans le prompt)
- Tu veux ajouter des tags thématiques (modifier la liste de tags)

Format de sortie attendu : JSON strict `{"score": int, "tag": str, "raison": str}`.
Ne pas changer ce format sans adapter le parsing dans `digest.py`.

### SYNTHESIS_PROMPT (Sonnet)

Définit le ton (pro, direct, pas de superlatifs), le format (Markdown
avec puces et liens sources), et la consigne de regroupement thématique.
À ajuster si :
- Les synthèses sont trop génériques → ajouter des exemples de bon digest
- Le ton est trop formel ou pas assez → modifier les instructions de style
- Tu veux un format différent (tableau, résumé exécutif…) → changer la section Format

### Bonnes pratiques pour itérer

1. **Changer une chose à la fois** et observer sur 2-3 runs avant de rechanger
2. **Versionner chaque changement** avec un message de commit descriptif
   (`git log` sur `prompt.py` devient ton historique d'expérimentation)
3. **Tester en local** avant de pousser :
   ```bash
   ANTHROPIC_API_KEY=sk-ant-... python digest.py
   ```
4. **Comparer les coûts** : un prompt plus long = plus de tokens Haiku
   sur 50 articles × 3 runs/jour × 30 jours = impact non négligeable

---

## 8. Coût détaillé

### Par run (estimation moyenne)

| Opération | Volume estimé | Coût estimé |
|---|---|---|
| Scoring Haiku (50 articles × ~500 tokens in/out) | ~25k tokens | ~0.01$ |
| Synthèse Sonnet (15 articles × ~300 tokens in, ~500 tokens out × 3 catégories) | ~12k tokens | ~0.04$ |
| **Total par run** | | **~0.05$** |

### Par mois

| Période | Coût |
|---|---|
| Par run | ~0.05$ |
| Par jour (3 runs) | ~0.15$ |
| Par mois | **~4.50$** |

### Infra

| Service | Coût |
|---|---|
| GitHub Actions (repo public) | Gratuit (minutes illimitées) |
| GitHub Pages (repo public) | Gratuit |
| **Total infra** | **0$** |

### Surveiller la conso

Sur [platform.claude.com](https://platform.claude.com) → **Usage** :
vérifier les premiers jours que la consommation correspond aux estimations.
Signe d'alerte : plus de 100k tokens Haiku/jour (bug de boucle probable).

---

## 9. Maintenance courante

### Un feed casse (erreur 404 ou timeout)

Dans les logs Actions (onglet Actions → dernier run → "Run digest"),
chercher les lignes :
```
! fetch error NOM_DU_FEED: ...
```
Corriger l'URL dans `sources.opml` ou commenter l'entrée le temps de
trouver la nouvelle URL.

### Trop peu d'articles dans le digest

Causes possibles et solutions :
- `LOOKBACK_HOURS` trop court → monter à 12 ou 16
- `MIN_SCORE` trop élevé → descendre à 2
- Sources peu actives → vérifier les feeds dans Reeder directement

### Trop de bruit dans le digest

- `MIN_SCORE` trop bas → monter à 4
- Profil dans `SCORING_PROMPT` trop large → affiner les critères
- Source particulièrement bruyante → retirer de l'OPML ou lui assigner
  une catégorie séparée avec un seuil plus élevé

### Mettre à jour les modèles Claude

Quand Anthropic sort de nouveaux modèles, mettre à jour dans `digest.py` :
```python
HAIKU_MODEL = "claude-haiku-X-X"
SONNET_MODEL = "claude-sonnet-X-X"
```

### Deprecation Node.js dans Actions (échéance juin 2026)

Warning actuel dans les logs :
> *"Node.js 20 actions are deprecated [...] forced to run with Node.js 24
> starting June 2nd, 2026"*

Action à faire avant juin 2026 — mettre à jour `digest.yml` :
```yaml
uses: actions/checkout@v4       →  actions/checkout@v5
uses: actions/setup-python@v5   →  actions/setup-python@v6
uses: peaceiris/actions-gh-pages@v4  →  version compatible Node 24
```

### Ajouter une source

1. Trouver l'URL du flux RSS (pattern courant : `/feed`, `/rss.xml`, `/atom.xml`)
2. Tester l'URL dans un navigateur (doit afficher du XML)
3. Ajouter dans `sources.opml` dans la catégorie appropriée :
   ```xml
   <outline type="rss" text="Nom du site"
            xmlUrl="https://exemple.com/feed"
            htmlUrl="https://exemple.com"/>
   ```
4. Commiter et pousser — pris en compte au prochain run automatiquement

---

## 10. Décisions de conception

### Pourquoi un seul item RSS par run et pas un item par article ?

Le digest est pensé comme un **bulletin éditorial**, pas comme un agrégateur.
Un item par run dans Reeder = "1 nouveau bulletin" 3x/jour, avec tout le
contenu dedans. Plus lisible qu'une liste de 20 items atomiques.
Inconvénient : si tu veux marquer un article spécifique comme "à relire",
c'est moins pratique. Alternative à implémenter si besoin : mode hybride
avec un item par article retenu + un item résumé.

### Pourquoi seen.json commité dans git et pas une base de données ?

Zéro infrastructure. Le fichier est petit (~50KB après 14 jours de rétention),
git gère les conflits proprement (le `[skip ci]` évite les boucles),
et l'historique des articles traités est versionné gratuitement.
SQLite sur le runner Actions serait réinitialisé à chaque run (éphémère).
Redis ou DynamoDB seraient overkill pour ce volume.

### Pourquoi deux modèles (Haiku + Sonnet) ?

Haiku est ~10x moins cher que Sonnet pour un résultat équivalent
sur des tâches simples de classification. Scorer 50 articles (JSON court,
décision binaire) ne nécessite pas les capacités de nuance de Sonnet.
La synthèse finale (regroupement thématique, ton éditorial, Markdown structuré)
justifie Sonnet. Ce split divise la facture mensuelle par ~3 par rapport
à un pipeline tout-Sonnet.

### Pourquoi l'OPML comme source de vérité et pas le code ?

Double usage : le même fichier `sources.opml` est lisible par le pipeline
Python (`ET.parse()`) ET importable directement dans Reeder, Feedly,
ou n'importe quel lecteur RSS standard. Ajouter une source = modifier l'OPML,
pas le code. Cela sépare aussi les préoccupations : un éditeur non-développeur
pourrait maintenir l'OPML sans toucher au code.

### Pourquoi arXiv cs.AI est dans la liste malgré le volume ?

arXiv sort 200+ papiers/jour. Le scoring Haiku filtre efficacement
(la plupart auront score 1-2 pour un profil RSSI/DSI). Le coût du scoring
est marginal (quelques centimes), et les rares papiers score 4-5 (nouveau
modèle, benchmark majeur) valent la peine d'être capturés.
Si le bruit persiste, ajouter un pré-filtre par mots-clés dans
`fetch_recent_articles()` avant d'appeler Haiku.

### Pourquoi MIT et pas Apache 2.0 ou AGPL ?

MIT pour ce projet spécifique : le code n'a rien d'innovant (pipeline
classique de curation), aucun brevet à protéger (→ Apache 2.0 inutile),
et aucune logique métier originale à préserver en open source
(→ AGPL inutile). MIT = friction minimale pour quiconque voudrait
s'en inspirer pour son propre digest.

### Pourquoi repo public et pas privé ?

Le repo contient uniquement du code générique et des flux de presse publique.
La seule donnée sensible (clé API Anthropic) est dans GitHub Secrets,
jamais dans le repo. Repo public = GitHub Pages gratuit + GitHub Actions
illimité + potentiel de partage avec d'autres. Aucun inconvénient réel
pour ce cas d'usage.

---

## 11. Pièges rencontrés au setup

Cette section documente les problèmes rencontrés lors du premier déploiement,
pour accélérer les prochaines installations.

### digest.yml placé à la racine du repo

**Symptôme** : onglet Actions ne montre que "pages build and deployment",
pas "Build digest". Le workflow semble ne pas exister.

**Cause** : GitHub Actions ne détecte les workflows que dans
`.github/workflows/`. Un fichier `digest.yml` à la racine est ignoré.
Les dossiers commençant par `.` sont cachés sur Mac/Linux et souvent
oubliés lors d'un upload via l'interface web GitHub.

**Solution** : sur GitHub, ouvrir `digest.yml` → crayon ✏️ → renommer
en `.github/workflows/digest.yml` (GitHub crée les dossiers automatiquement
quand tu tapes `/` dans le nom du fichier).

### Erreur `Client.__init__() got an unexpected keyword argument 'proxies'`

**Symptôme** : step "Run digest" échoue en 1s avec TypeError.

**Cause** : conflit de version entre `anthropic==0.39.0` (trop ancienne)
et la version de `httpx` installée par défaut sur le runner GitHub Actions.

**Solution** : dans `requirements.txt`, remplacer :
```
anthropic==0.39.0
```
par :
```
anthropic>=0.49.0
httpx>=0.27.0
```

### GitHub Pages inactif après le premier run

**Symptôme** : la branche `gh-pages` existe mais l'URL renvoie 404.

**Cause** : GitHub Pages ne s'active pas automatiquement, il faut
le configurer manuellement **après** la création de la branche `gh-pages`
par le premier run réussi.

**Solution** : Settings → Pages → Deploy from a branch → `gh-pages` /
`/ (root)` → Save. Attendre 2 minutes.

### "Articles frais trouvés : 0" au premier run

**Symptôme** : le workflow tourne sans erreur mais ne génère rien.

**Cause** : `LOOKBACK_HOURS = 8` ne capture rien si les sources n'ont
pas publié dans les 8 dernières heures (nuit, week-end, sources peu actives).

**Solution** : modifier temporairement `LOOKBACK_HOURS = 48` dans
`digest.py` pour le premier test, puis remettre à 8.

### Deux workflows "Queued" en parallèle

**Symptôme** : onglet Actions montre deux runs "pages build and deployment"
bloqués en Queued.

**Cause** : GitHub Pages avait été activé sur la branche `main` au lieu
de `gh-pages`, ce qui déclenchait le workflow Pages automatique en boucle.

**Solution** : Settings → Pages → changer la source pour `gh-pages`
(ou désactiver Pages temporairement, faire tourner le workflow digest,
puis réactiver sur `gh-pages`).

---

## 12. Améliorations futures

Ces améliorations sont intentionnellement hors du scope du MVP.
À implémenter après validation du pipeline sur 2-4 semaines d'usage réel.

### Court terme (semaines 2-4)

- **Retry sur les appels API** : un blip réseau fait planter le run.
  Ajouter `tenacity` ou une boucle `try/except` avec backoff exponentiel.
- **Batch scoring** : les 50 appels Haiku séquentiels prennent ~30s.
  L'[API Batch d'Anthropic](https://docs.anthropic.com/en/api/creating-message-batches)
  permettrait de les envoyer en parallèle avec 50% de réduction de coût en prime.
- **Alertes sur feeds cassés** : log structuré des erreurs de fetch,
  envoi d'une notification quand un feed échoue X fois de suite.

### Moyen terme (mois 2-3)

- **Filtre cybersécurité dédié** : ajouter les flux CERT-FR, ANSSI alertes,
  CISA KEV dans une catégorie "Cyber FR" avec un prompt de scoring
  spécialisé (criticité CVE, périmètre DICP…).
- **Pré-filtre arXiv par mots-clés** : avant le scoring Haiku, filtrer
  les titres arXiv par liste de mots-clés pertinents (LLM, agent, security,
  reasoning…) pour réduire le volume entrant.
- **Déduplication cross-sources** : regrouper les articles qui parlent
  du même sujet avant la synthèse (clustering par similarité de titre
  via embeddings ou simple Jaccard sur les tokens).

### Long terme

- **Mémoire des sujets** : PGVector + embeddings pour détecter les
  thèmes récurrents sur plusieurs semaines et adapter le scoring
  ("ce sujet a déjà été couvert 3 fois ce mois, baisser le score").
- **Feedback loop** : mécanisme pour signaler les articles mal scorés
  et affiner le prompt automatiquement.
- **Migration vers GitHub Actions native Pages** : remplacer
  `peaceiris/actions-gh-pages@v4` par les actions officielles
  `actions/upload-pages-artifact` + `actions/deploy-pages`
  (plus maintenu, plus stable, recommandé par GitHub).
