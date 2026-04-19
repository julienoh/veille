# Veille IA — Digest personnel

Pipeline de curation IA + cybersécurité. Lit des flux RSS, filtre avec
Claude Haiku, synthétise avec Claude Sonnet, expose un RSS prêt pour Reeder.

## Setup initial (5 min)

1. **Fork ou clone ce repo** (public pour bénéficier de GitHub Pages gratuit +
   minutes Actions illimitées).

2. **Activer GitHub Pages** : Settings → Pages → Source = Deploy from branch →
   Branch = `gh-pages` (créée automatiquement au premier run).

3. **Ajouter le secret API** : Settings → Secrets and variables → Actions →
   New repository secret → Name = `ANTHROPIC_API_KEY`, Value = ta clé.

4. **Ajuster `DIGEST_URL`** dans `digest.py` pour pointer vers
   `https://<ton-user>.github.io/<nom-repo>/digest.xml`.

5. **Copier ton OPML** dans `sources.opml` à la racine.

6. **Premier run manuel** : Actions → "Build digest" → Run workflow. Si tout
   est vert, le fichier `output/digest.xml` est généré et publié.

7. **Abonner Reeder** à l'URL `https://<ton-user>.github.io/<nom-repo>/digest.xml`.

## Tuning

- **`LOOKBACK_HOURS`** : période regardée à chaque run (8h par défaut = 3 runs/jour
  qui se recouvrent un peu, pour ne rien rater).
- **`MIN_SCORE`** : seuil de pertinence (3 = utile, 4 = intéressant, 5 = incontournable).
  Commence à 3, monte à 4 si trop de bruit.
- **`MAX_ARTICLES_PER_CATEGORY`** : garde-fou anti-explosion de coûts.
- **`prompt.py`** : c'est LÀ qu'on itère pour améliorer le digest. Les deux
  prompts (scoring, synthèse) sont isolés pour faciliter les tests.

## Coût approximatif

Par run : ~50 articles scorés par Haiku (~1500 tokens in/out total) +
~10-20 articles synthétisés par Sonnet (~3000 tokens in/out).
Soit ~0.05$ par run, ~0.15$/jour, ~5$/mois.
