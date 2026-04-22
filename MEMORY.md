# Memory — projet veille

> Fichier de mémoire de travail partagé entre jul_oh et Claude.
> Se lit au début de chaque nouvelle conversation pour reprendre le contexte.
> Se met à jour à la fin de chaque session productive.

**Dernière mise à jour** : 2026-04-22

---

## État actuel

Pipeline de curation RSS → digest IA **opérationnel en production** depuis
le 2026-04-19. Tourne 3x/jour via GitHub Actions, synthétise avec Claude
Haiku (scoring) + Sonnet (synthèse), servi par GitHub Pages, consommé
dans Reeder iOS.

- Repo : https://github.com/julienoh/veille (public, MIT)
- URL digest : https://julienoh.github.io/veille/digest.xml
- Coût réel constaté : ~0.05$ par run

---

## Décisions prises

### Architecture

- **2026-04-19** — GitHub Actions comme cron (vs VPS, Raspberry Pi, n8n)
  → zéro infra à maintenir, gratuit, versionné, logs intégrés
- **2026-04-19** — GitHub Pages comme serveur RSS (vs Cloudflare R2, Netlify)
  → même repo, zéro config supplémentaire
- **2026-04-20** — Repo public (vs privé)
  → GitHub Pages gratuit sur repo public uniquement, rien de sensible dans le code
  (la clé API est dans GitHub Secrets, jamais dans le repo)
- **2026-04-19** — OPML comme source de vérité des sources (vs URLs hardcodées)
  → double usage : lisible par le pipeline ET importable dans Reeder

### Modèles Claude

- **2026-04-19** — Split Haiku (scoring) + Sonnet (synthèse) (vs tout-Sonnet)
  → Haiku ~10x moins cher pour une tâche de classification simple,
  économise ~65% sur la facture mensuelle
- **2026-04-19** — Modèles retenus : `claude-haiku-4-5-20251001` et `claude-sonnet-4-6`

### Stockage et état

- **2026-04-19** — `seen.json` commité dans git (vs SQLite, Redis, DynamoDB)
  → zéro infra, versionné gratuitement, fenêtre 14 jours ~50KB max
- **2026-04-19** — Un seul item RSS par run (vs un par article)
  → format "bulletin" plus lisible dans Reeder, moins d'items à marquer lus

### Licence et ouverture

- **2026-04-21** — Licence MIT (vs Apache, AGPL, pas de licence)
  → code générique sans enjeu de brevet ni logique métier originale,
  friction minimale pour un éventuel fork

---

## En cours

**Enrichissement du contenu des articles** : les feeds RSS sont souvent
tronqués par les éditeurs. La synthèse Sonnet est donc basée sur des
résumés courts, ce qui limite la qualité.

Trois solutions envisagées, aucune encore implémentée :

1. **Jina Reader** (`r.jina.ai`) — le plus simple, zéro infra, appel HTTP
2. **Wallabag self-hosted** — meilleure qualité d'extraction, nécessite un serveur
3. **wallabag.it** — service gratuit hébergé, quota limité

Sous-question ouverte : l'hébergement Hostinger de jul_oh est-il un
shared hosting (incompatible Wallabag) ou un VPS (compatible) ?
À clarifier avant de trancher.

---

## Questions ouvertes

- **Hostinger** : type exact du plan (shared vs VPS) ?
  Conditionne le choix entre wallabag.it et self-hosted
- **Stratégie de fallback** : Wallabag → Jina → résumé feed, ou
  directement Jina partout ? À décider une fois le test effectué
- **Paywalls** (FT, Bloomberg, The Information) : laisser tels quels
  ou chercher une solution ? Pour l'instant laissés tels quels, décision
  à réévaluer si des articles importants passent à côté du radar

---

## Idées en réserve

### Court terme

- Retry sur les appels API avec `tenacity` ou backoff exponentiel
- Batch scoring via l'API Batch d'Anthropic (50% de réduction + parallélisme)
- Alertes sur feeds cassés (log structuré + notification après N échecs)

### Moyen terme

- Catégorie "Cyber FR" dédiée avec CERT-FR, ANSSI, CISA KEV +
  prompt de scoring spécialisé (criticité CVE, DICP)
- Pré-filtre arXiv par mots-clés avant le scoring Haiku
  (réduire le volume entrant sur cette source très bruyante)
- Déduplication cross-sources via clustering de titres
  (embeddings ou Jaccard sur tokens)

### Long terme

- Mémoire des sujets via PGVector + embeddings
  (adapter le scoring si un sujet a déjà été couvert N fois ce mois)
- Feedback loop pour signaler les articles mal scorés
  (et affiner le prompt automatiquement)
- Migration vers actions Pages natives
  (`actions/upload-pages-artifact` + `actions/deploy-pages`)

---

## Problèmes connus

- **Warning Node.js 20 deprecation** dans les logs Actions
  (échéance juin 2026, à corriger avant en mettant à jour les versions
  d'actions dans `digest.yml`)
- **Feeds probablement cassés non identifiés** : certaines URLs de l'OPML
  sont des patterns probables non vérifiés individuellement
  (`/feed`, `/rss`) qui peuvent retourner 404. À identifier dans les logs
  sur 1-2 semaines d'usage réel.
- **Message trompeur "To get started, purchase credits"** sur platform.claude.com
  peut s'afficher même avec un solde positif (UI incohérente côté Anthropic)

---

## Historique des runs notables

- **2026-04-19 20:11 UTC** — Premier run réussi en production
  44 sources chargées, 20 articles frais, 3 retenus, digest.xml écrit,
  branche gh-pages créée

---

## Pattern de travail avec Claude

**À la fin d'une conversation productive** :
> "Résume ce qu'on a fait dans cette conversation et propose les mises
> à jour de MEMORY.md, CHANGELOG.md et README.md si nécessaire."

**Au début d'une nouvelle conversation** (si MCP GitHub activé) :
Claude lit ce fichier en premier pour reprendre le contexte sans avoir
à tout recoller manuellement.

**Activation MCP GitHub** : app Claude → Settings → Connectors → GitHub →
connecter compte. À faire une fois pour toutes.
