# Veille IA & Cyber — Digest personnel

Pipeline de curation automatique : lit des flux RSS, filtre en deux phases
puis synthétise avec des LLM, expose un flux RSS consommable dans Reeder (iOS).

**URL du digest** : https://julienoh.github.io/veille/digest.xml
**Licence** : MIT
**Fréquence** : 3 digests/jour (7h, 13h, 19h heure de Paris)
**Coût estimé** : ~17$/mois (API LLM uniquement, infra gratuite)

---

## Table des matières

1. [Architecture](#1-architecture)
2. [Structure du repo](#2-structure-du-repo)
3. [Sources OPML](#3-sources-opml)
4. [Setup complet](#4-setup-complet)
5. [Paramètres de tuning](#5-paramètres-de-tuning)
6. [Maintenance](#6-maintenance)
7. [Choix techniques](#7-choix-techniques)
8. [Roadmap](#8-roadmap)

---

## 1. Architecture

Le pipeline est agnostique du LLM côté conception (deux rôles : *LLM de filtrage*
et *LLM de synthèse*). L'implémentation actuelle utilise le SDK Anthropic
(modèles configurables dans `digest.py`).

### Vue d'ensemble

```
sources.opml
    │
    ▼
digest.py  ←─── cron 3x/jour (GitHub Actions)
    │
    ├── 1. Charge les sources depuis l'OPML
    ├── 2. Fetch les flux RSS (feedparser)
    ├── 3. Filtre les articles < LOOKBACK_HOURS non déjà vus (seen.json)
    │
    ├── 4. PHASE 1 — Scoring (LLM de filtrage, 1 appel par article)
    │       Sortie : {score, decision, tag, confiance, signal_principal, …}
    │       Filtre : on garde decision ∈ {read_now, read_later}
    │
    ├── 5. PHASE 2 — Déduplication (LLM de filtrage, 1 appel par catégorie OPML)
    │       Identifie les clusters de doublons, garde l'article canonique
    │       Les autres : decision=archive, score=2 (rétrogradés, pas supprimés)
    │
    ├── 6. PHASE 3 — Synthèse (LLM de synthèse, 1 appel par catégorie OPML)
    │       Markdown éditorial : 1-2 phrases par sujet, regroupement thématique
    │
    └── 7. Génère output/digest.xml (RSS, 1 item par run)
            │
            ├──► git commit → branche main (seen.json + digest.xml)
            └──► branche gh-pages → GitHub Pages → Reeder (iOS)
```

### Flux de données

```
OPML (catégories → feeds)
  └─► feedparser.parse(url) — par source
        └─► filtre temporel : published > now - LOOKBACK_HOURS
              └─► filtre doublon URL : sha1(url)[:12] pas dans seen.json
                    │
                    ▼  PHASE 1
                    LLM de filtrage
                    input : titre + source + résumé (400 chars max)
                    output : JSON enrichi (score 1-5, decision, tag,
                             confiance, signal_principal, plafond_appliqué)
                    └─► filtre : decision ∈ {read_now, read_later}
                          │
                          ▼  groupement par catégorie OPML
                          │
                          ▼  PHASE 2
                          LLM de filtrage
                          input : liste indexée des articles d'une catégorie
                          output : clusters de doublons + canonical_id
                          action : rétrograde les non-canoniques en archive
                                │
                                ▼  PHASE 3
                                LLM de synthèse (par catégorie)
                                input : articles dédupliqués
                                output : Markdown avec puces et liens
                                      └─► feedgen → digest.xml (RSS 2.0)
                                            └─► 1 item RSS par run
```

### LLMs utilisés

| Rôle | Configuration `digest.py` | Justification |
|---|---|---|
| Filtrage (phases 1 et 2) | `FILTERING_MODEL` | Tâche simple de classification, JSON court, volume élevé → modèle économique |
| Synthèse (phase 3) | `SYNTHESIS_MODEL` | Nuance, regroupement thématique, ton éditorial → modèle plus capable |

### Fournisseurs supportés

L'abstraction `llm_client.py` route les appels selon le préfixe du nom de
modèle. Deux fournisseurs supportés en natif :

| Préfixe | Fournisseur | Clé API à fournir | Exemple |
|---|---|---|---|
| `anthropic/` | Anthropic (SDK natif) | `ANTHROPIC_API_KEY` | `anthropic/claude-haiku-4-5-20251001` |
| `openrouter/` | OpenRouter (SDK OpenAI, base_url custom) | `OPENROUTER_API_KEY` | `openrouter/openai/gpt-5`, `openrouter/google/gemini-2.5-flash` |

Les deux phases peuvent utiliser des fournisseurs différents (ex : filtrage
via Anthropic direct pour le caching, synthèse via OpenRouter pour tester
un autre modèle). Il suffit de définir les variables d'env correspondantes.

Pour ajouter un troisième fournisseur (Mistral direct, Together, etc.),
étendre `llm_client.py` avec un nouveau préfixe et un client dédié.

---

## 2. Structure du repo

```
veille/
├── .github/
│   └── workflows/
│       └── digest.yml        # Workflow GitHub Actions (cron + deploy)
├── output/
│   └── digest.xml            # Flux RSS généré, commité + servi par Pages
├── digest.py                 # Pipeline complet (load, fetch, score, dédup, synth)
├── llm_client.py             # Mini-abstraction LLM (route anthropic/ vs openrouter/)
├── prompt.py                 # Prompts LLM isolés (itérables indépendamment du code)
├── requirements.txt          # feedparser, feedgen, anthropic, openai, httpx
├── seen.json                 # Hashes SHA1 des articles traités (fenêtre 14 jours)
├── sources.opml              # Sources organisées par catégorie
├── LICENSE                   # MIT
└── README.md                 # Ce fichier
```

### Rôle de chaque fichier

**`digest.py`** : pipeline complet. Toute la logique métier : chargement OPML,
fetch RSS, déduplication URL, scoring (phase 1), déduplication sémantique
(phase 2), synthèse (phase 3), génération RSS. La section `Configuration`
en haut regroupe tous les paramètres ajustables.

**`prompt.py`** : trois prompts LLM isolés (`SCORING_PROMPT`, `DEDUP_PROMPT`,
`SYNTHESIS_PROMPT`). Découplage intentionnel : on itère sur les prompts sans
risquer de casser la logique Python, et l'historique git des changements
de prompts est séparé de celui du code.

**`sources.opml`** : source de vérité des feeds. Le script le lit à chaque run —
modifier l'OPML suffit pour ajouter/retirer une source. Même fichier utilisable
dans Reeder pour abonnement direct.

**`seen.json`** : dictionnaire `{hash: date_iso}` des articles déjà traités.
Commité à chaque run via `git commit -m "Update digest [skip ci]"`.
La fenêtre glissante de `SEEN_RETENTION_DAYS` évite la croissance infinie.

**`digest.yml`** : workflow GitHub Actions. Trois déclencheurs : cron 3x/jour,
`workflow_dispatch` (bouton manuel), push sur main.

---

## 3. Sources OPML

Le fichier `sources.opml` est organisé en catégories (premier niveau d'outline)
qui contiennent chacune des feeds (deuxième niveau). Seuls les outlines avec
un attribut `xmlUrl` sont fetchés ; les sources documentées sans RSS sont
ignorées silencieusement par le pipeline mais restent visibles dans l'OPML.

Catégories actuelles :
- **Sources françaises IA** : Actu IA, Usine Digitale, Frenchweb, Next.ink…
- **Grandes sources internationales** : The Batch, MIT Technology Review,
  VentureBeat AI, TechCrunch AI, Wired AI, Ars Technica…
- **Labos & éditeurs** : OpenAI, DeepMind, Anthropic (feed tiers),
  Hugging Face, NVIDIA…
- **Recherche & veille technique** : arXiv cs.AI, arXiv cs.LG,
  HF Daily Papers (feed tiers), EleutherAI, LessWrong AI
- **Automatisation & agents** : LangChain, LlamaIndex, n8n, Relevance AI

### Sources sans RSS officiel

Plusieurs sources de référence n'ont pas de flux RSS direct :
- **Anthropic, HF Daily Papers** : feeds tiers générés par
  [Olshansk/rss-feeds](https://github.com/Olshansk/rss-feeds) ou
  [takara.ai](https://papers.takara.ai/api/feed). Fiables en pratique
  mais dépendants d'un mainteneur tiers.
- **Mistral, Bloomberg Tech, FT AI, The Information, Superhuman AI** :
  pas de RSS officiel, paywall ou newsletter. Pour les newsletters,
  utiliser [Kill the Newsletter](https://kill-the-newsletter.com) qui
  convertit n'importe quelle newsletter email en flux RSS.

### Ajouter une source

1. Trouver l'URL du flux RSS (patterns courants : `/feed`, `/rss.xml`, `/atom.xml`).
2. Tester l'URL dans un navigateur (doit afficher du XML).
3. Ajouter dans `sources.opml` dans la catégorie appropriée :
   ```xml
   <outline type="rss" text="Nom du site"
            xmlUrl="https://exemple.com/feed"
            htmlUrl="https://exemple.com"/>
   ```
4. Commiter et pousser — pris en compte au prochain run automatiquement.

---

## 4. Setup complet

### Prérequis

- Compte GitHub gratuit.
- Compte chez au moins un des fournisseurs LLM supportés :
  - [platform.claude.com](https://platform.claude.com) (Anthropic)
  - [openrouter.ai](https://openrouter.ai) (OpenRouter — accès multi-modèles)
- ~20$ de crédits sur le fournisseur choisi suffisent pour 1-2 mois.

### Étape 1 — Cloner ou forker ce repo

```bash
git clone https://github.com/julienoh/veille.git
cd veille
```

### Étape 2 — Adapter les sources (optionnel)

Modifier `sources.opml` pour ajouter tes propres sources ou retirer celles
qui ne t'intéressent pas. Format standard OPML, importable dans n'importe
quel lecteur RSS.

### Étape 3 — Ajuster `DIGEST_URL` dans `digest.py`

```python
# digest.py, section Configuration
DIGEST_URL = "https://TON-USER.github.io/NOM-REPO/digest.xml"
```

### Étape 4 — Créer le repo GitHub

- Repo **public** (obligatoire pour GitHub Pages gratuit).
- Pousser tous les fichiers sur la branche `main`.
- Vérifier que `.github/workflows/digest.yml` est bien présent.

### Étape 5 — Générer et configurer la clé API

1. Aller sur le portail du fournisseur LLM choisi.
2. **Settings → API Keys → Create Key**.
3. Copier la clé immédiatement (affichée une seule fois).
4. Dans le repo GitHub : **Settings → Secrets and variables → Actions →
   New repository secret**.
   - Pour Anthropic : `ANTHROPIC_API_KEY`.
   - Pour OpenRouter : `OPENROUTER_API_KEY`.
   - Tu peux ajouter les deux si tu veux mixer (filtrage Anthropic, synthèse OpenRouter).
   - Value : coller la clé.

> Ne jamais mettre la clé dans le code ou dans un fichier du repo. GitHub
> Secrets est le seul endroit approprié.

Si tu utilises OpenRouter, ajoute aussi `OPENROUTER_API_KEY` dans le step
`env:` du workflow `.github/workflows/digest.yml` (à côté de `ANTHROPIC_API_KEY`).

### Étape 6 — Configurer les limites de dépenses

Sur le portail du fournisseur LLM, **Settings → Billing → Limits** :
- Monthly budget limit : 20-30$ (protection contre les bugs de boucle).
- Désactiver l'auto-reload.

### Étape 7 — Premier run manuel

**Actions → Build digest → Run workflow → branche `main` → Run workflow**.

Attendre ~2 minutes. Vérifier dans les logs :
```
Sources chargées : XX
Articles frais trouvés : XX
Phase 1 terminée : XX articles retenus
Phase 2 terminée : XX articles après dédup
✓ Digest écrit dans output/digest.xml
```

Si `Articles frais trouvés : 0` : passer temporairement `LOOKBACK_HOURS = 48`
dans `digest.py` pour un premier test, puis remettre à 8.

### Étape 8 — Activer GitHub Pages

Après un premier run réussi (la branche `gh-pages` est créée automatiquement) :

**Settings → Pages → Source = Deploy from a branch →
Branch = `gh-pages` / `/ (root)` → Save**.

Attendre 2 minutes, puis vérifier :
```
https://TON-USER.github.io/NOM-REPO/digest.xml
```

### Étape 9 — Abonner Reeder (iOS)

Reeder → **+** → coller l'URL → valider.

---

## 5. Paramètres de tuning

Tous dans `digest.py`, section `Configuration` en haut du fichier.

| Paramètre | Défaut | Quand changer |
|---|---|---|
| `LOOKBACK_HOURS` | 8 | Monter à 12 si trop peu d'articles la nuit. Les 3 runs/jour se recouvrent légèrement avec 8h, ce qui évite les trous. |
| `ACCEPTED_DECISIONS` | `{"read_now", "read_later"}` | Ajouter `"skim"` si tu veux récupérer les articles survolables. Retirer `"read_later"` pour un digest "urgent only". |
| `MAX_ARTICLES_PER_CATEGORY` | 20 | Baisser à 10 si la facture LLM monte. Garde-fou contre les pics (ex: arXiv). |
| `SEEN_RETENTION_DAYS` | 14 | Fenêtre de déduplication URL. 14 jours = un article vu cette semaine ne reviendra pas la semaine prochaine. |
| `FILTERING_MODEL` | `anthropic/claude-haiku-4-5-20251001` | Modèle utilisé pour les phases 1 et 2. Préférer un petit modèle économique. Format `<provider>/<nom>` cf. §1. |
| `SYNTHESIS_MODEL` | `anthropic/claude-sonnet-4-6` | Modèle utilisé pour la phase 3. Préférer un modèle plus capable pour le ton et le regroupement. Format `<provider>/<nom>` cf. §1. |

### Grille de scoring (synthèse)

Le détail (critères, exemples, plafonds) vit dans `prompt.py` (`SCORING_PROMPT`).
Synthèse pour avoir le réflexe sans ouvrir le prompt :

| Score | Niveau | Décision typique |
|---|---|---|
| 5 | Incontournable (CVE exploitée, modèle SOTA, décision ANSSI…) | `read_now` |
| 4 | Intéressant (vuln importante, étude solide, release majeure) | `read_now` ou `read_later` |
| 3 | Utile si du temps (tutoriel, REX, analyse correcte) | `read_later` ou `skim` |
| 2 | Marginal (annonce mineure, opinion peu argumentée) | `skim` ou `archive` |
| 1 | Bruit (clickbait, communiqué pur, méta-annonce) | `archive` |

Critères transverses pondérés par le LLM : **Nouveauté**, **Actionabilité**
(impact RSSI/DSI), **Fiabilité** (source primaire vs PR), **Profondeur**.

Plafonds explicites (vue d'ensemble — détail dans `prompt.py`) :
- Levée de fonds sans contenu technique : max 2.
- Étude sponsorisée par un vendeur : max 2.
- Article basé seulement sur un tweet/post : max 2.
- Roadmap sans livrable disponible : max 3.

### Tags disponibles

`ia_recherche` · `ia_produit` · `cyber_vuln` · `cyber_strategie` ·
`dev_tooling` · `business` · `autre`.

### Itérer sur les prompts

Trois prompts dans `prompt.py`. Bonnes pratiques :
1. Changer une chose à la fois et observer sur 2-3 runs avant de rechanger.
2. Versionner chaque changement avec un message de commit descriptif
   (`git log` sur `prompt.py` devient ton historique d'expérimentation).
3. Tester en local : `ANTHROPIC_API_KEY=sk-... python3 digest.py`.
4. Surveiller les coûts : un prompt plus long = plus de tokens × volume.

---

## 6. Maintenance

### Un feed casse (erreur 404, timeout)

Dans les logs Actions → dernier run → "Run digest", chercher :
```
! fetch error NOM_DU_FEED: ...
```
Corriger l'URL dans `sources.opml` ou commenter l'entrée le temps de
trouver la nouvelle URL.

### Trop peu d'articles dans le digest

- `LOOKBACK_HOURS` trop court → monter à 12 ou 16.
- `ACCEPTED_DECISIONS` trop restrictif → ajouter `"skim"`.
- Sources peu actives → vérifier directement dans Reeder.

### Trop de bruit dans le digest

- `ACCEPTED_DECISIONS` trop large → retirer `"read_later"` ou `"skim"`.
- Profil dans `SCORING_PROMPT` trop large → affiner les critères.
- Plafonds insuffisants → ajouter des cas dans le bloc "Plafonds obligatoires".
- Source particulièrement bruyante → retirer de l'OPML ou la déplacer dans
  une catégorie séparée.

### Trop de doublons restent

- Vérifier les logs de la phase 2 : `dédup CATEGORIE : N doublon(s) rétrogradé(s)`.
- Si N = 0 alors que tu vois des doublons : affiner `DEDUP_PROMPT` (exemples,
  critères de canonical_id, granularité du "même sujet factuel").
- La phase 2 est intra-catégorie : les doublons cross-catégorie ne sont pas
  détectés actuellement (cf. roadmap).

### Mettre à jour les modèles LLM

Quand le fournisseur publie de nouveaux modèles, mettre à jour dans `digest.py` :
```python
FILTERING_MODEL = "..."
SYNTHESIS_MODEL = "..."
```

### Deprecation Node.js dans Actions (échéance juin 2026)

Warning actuel dans les logs :
> *"Node.js 20 actions are deprecated [...] forced to run with Node.js 24
> starting June 2nd, 2026"*

À faire avant juin 2026 — mettre à jour `digest.yml` :
```yaml
uses: actions/checkout@v4       →  actions/checkout@v5
uses: actions/setup-python@v5   →  actions/setup-python@v6
uses: peaceiris/actions-gh-pages@v4  →  version compatible Node 24
```

### Surveiller la conso

Vérifier les premiers jours sur le portail du fournisseur LLM que la
consommation correspond aux estimations. Signe d'alerte : ×3 sur le volume
attendu = probable bug de boucle ou prompt qui retourne du texte trop long.

---

## 7. Choix techniques

### Pourquoi un pipeline de filtrage en deux phases ?

Phase 1 (scoring) note chaque article isolément — efficace mais ne voit pas
les doublons. Phase 2 (déduplication) compare uniquement les articles
score 3-5 entre eux, ce qui élimine le bruit sémantique (deux médias qui
relayent la même CVE) sans surcoût inutile sur les articles déjà jetés
en phase 1. Séparer évite aussi qu'un prompt unique devienne illisible.

### Pourquoi un projet agnostique du LLM ?

Le découplage *rôle / modèle* (LLM de filtrage vs LLM de synthèse) permet
de mixer les fournisseurs, changer un seul modèle sans toucher au reste,
et de bénéficier rapidement des nouvelles versions sans réécrire la doc.
L'implémentation actuelle utilise Anthropic, mais le design ne l'impose pas.

### Pourquoi GitHub Actions + Pages ?

Zéro infrastructure à maintenir, gratuit sur repo public, logs intégrés,
versionné. Alternatives écartées : VPS (charge mentale d'admin),
n8n (UX limitée pour la logique fine), Claude Code en `-p` (besoin d'une
machine allumée). Tradeoff : on dépend de GitHub côté disponibilité.

### Pourquoi l'OPML comme source de vérité ?

Double usage : le même fichier est lisible par le pipeline Python
(`ET.parse()`) ET importable directement dans Reeder, Feedly, ou n'importe
quel lecteur RSS standard. Ajouter une source = modifier l'OPML, pas le code.
Cela sépare aussi les préoccupations : un éditeur non-développeur pourrait
maintenir l'OPML sans toucher au code.

### Pourquoi `seen.json` commité dans git et pas une base de données ?

Zéro infrastructure. Le fichier reste petit (quelques dizaines de KB après
14 jours de rétention), git gère les conflits proprement (le `[skip ci]`
évite les boucles), et l'historique des articles traités est versionné
gratuitement. SQLite sur le runner Actions serait réinitialisé à chaque run
(éphémère). Redis ou DynamoDB seraient overkill pour ce volume.

### Pourquoi deux modèles (filtrage + synthèse) au lieu d'un seul ?

Un modèle économique sur de la classification simple coûte ~10× moins cher
qu'un modèle haut de gamme, pour un résultat équivalent sur scoring +
déduplication. La synthèse finale (regroupement thématique, ton éditorial,
Markdown structuré) justifie le modèle plus capable. Ce split divise la
facture totale par un facteur significatif vs un pipeline mono-modèle.

### Pourquoi un seul item RSS par run ?

Le digest est un **bulletin éditorial**, pas un agrégateur. Un item par run
dans Reeder = "1 nouveau bulletin" 3×/jour, avec tout le contenu dedans.
Plus lisible qu'une liste de 20 items atomiques. Inconvénient : si on veut
marquer un article spécifique comme "à relire", c'est moins pratique
(alternative possible : mode hybride avec un item par article retenu +
un item résumé).

### Pourquoi MIT et repo public ?

Le code n'a rien d'innovant (pipeline classique de curation), aucune logique
métier originale à protéger. MIT = friction minimale pour quiconque voudrait
s'en inspirer. Repo public = GitHub Pages gratuit + Actions illimité +
partage possible. La seule donnée sensible (clé API) est dans GitHub Secrets,
jamais dans le repo.

---

## 8. Roadmap

### Court terme

- **Retry sur les appels LLM** : un blip réseau fait planter un article.
  Ajouter `tenacity` ou une boucle `try/except` avec backoff exponentiel.
- **Batch scoring** : les ~50 appels phase 1 séquentiels prennent ~30s.
  L'API Batch (chez Anthropic et d'autres fournisseurs) permettrait de les
  envoyer en parallèle avec ~50% de réduction de coût.
- **Alertes sur feeds cassés** : log structuré des erreurs de fetch, envoi
  d'une notification quand un feed échoue X fois de suite.
- **Logs structurés des décisions** : exporter `signal_principal` et
  `plafond_appliqué` dans un fichier d'audit pour itérer sur le prompt
  à partir de données réelles.

### Moyen terme

- **Déduplication cross-catégorie** : la phase 2 actuelle travaille par
  catégorie OPML. Étendre à une dédup globale (ou par paire de catégories
  proches) pour attraper les doublons entre "Sources FR" et "Sources
  internationales" sur un même incident.
- **Filtre cybersécurité dédié** : ajouter CERT-FR, ANSSI alertes, CISA KEV
  dans une catégorie "Cyber FR" avec un prompt de scoring spécialisé
  (criticité CVE, périmètre DICP…).
- **Pré-filtre arXiv par mots-clés** : avant la phase 1, filtrer les titres
  arXiv par liste de mots-clés pertinents pour réduire le volume entrant
  et la facture LLM.

### Long terme

- **Mémoire des sujets** : embeddings + index vectoriel pour détecter les
  thèmes récurrents sur plusieurs semaines et adapter le scoring
  ("ce sujet a déjà été couvert 3 fois ce mois, baisser le score").
- **Feedback loop** : mécanisme pour signaler les articles mal scorés
  et affiner le prompt automatiquement.
- **Migration vers GitHub Actions native Pages** : remplacer
  `peaceiris/actions-gh-pages@v4` par les actions officielles
  `actions/upload-pages-artifact` + `actions/deploy-pages`.
- **Mode multi-fournisseur** : abstraire le client LLM derrière une
  interface commune pour permettre de mixer ou basculer entre fournisseurs.
