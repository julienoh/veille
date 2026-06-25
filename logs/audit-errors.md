# Audit erreurs — 30 derniers jours

Rétention glissante 30 jours. Append en bas. Aucune ligne pour un run
donné == pipeline sain. Phases : `fetch` (feed RSS), `scoring` (phase 1),
`dedup` (phase 2), `synthese` (phase 3).

| Date UTC | Phase | Cible | Erreur |
|---|---|---|---|
| 2026-06-22 08:10 UTC | scoring | Les LLM lisent-ils vraiment vos données structurées ? (Frenchweb) | TypeError: 'NoneType' object is not subscriptable |
| 2026-06-23 11:50 UTC | dedup | IA — Recherche | JSON malformé renvoyé par le LLM (Expecting ',' delimiter: line 56 column 6 (char 2261)) |
| 2026-06-24 09:13 UTC | dedup | IA — Recherche | JSON malformé renvoyé par le LLM (Expecting ',' delimiter: line 74 column 6 (char 2671)) |
| 2026-06-25 09:27 UTC | dedup | IA — Recherche | JSON malformé renvoyé par le LLM (Expecting ',' delimiter: line 62 column 6 (char 2610)) |
