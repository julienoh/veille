# Synthèse pipeline — 30 derniers jours

Rétention glissante 30 jours. Append en bas (le plus récent en bas).

- `Trouvés` : articles frais après filtrage URL/date.
- `RN` / `RL` / `Skim` : retenus en read_now / read_later / skim (entrent dans le digest).
- `Arch` : non retenu (decision = archive).
- `Dédup` : articles rétrogradés par la phase 2.
- `Err` : erreurs survenues (cliquable → audit-errors.md).
- `Retenue%` : (RN + RL + Skim) / Trouvés.

| Date UTC | Filtrage | Synthèse | Trouvés | RN | RL | Skim | Arch | Dédup | Err | Retenue% |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-06-19 20:20 UTC | dsv4-flash | dsv4-pro | 0 | 0 | 0 | — | 0 | 0 | 0 | — |
| 2026-06-20 09:20 UTC | dsv4-flash | dsv4-pro | 10 | 0 | 0 | — | 10 | 0 | 0 | 0% |
| 2026-06-20 14:10 UTC | dsv4-flash | dsv4-pro | 9 | 0 | 0 | — | 9 | 0 | 0 | 0% |
| 2026-06-20 19:41 UTC | dsv4-flash | dsv4-pro | 4 | 0 | 0 | — | 4 | 0 | 0 | 0% |
| 2026-06-21 09:54 UTC | dsv4-flash | dsv4-pro | 12 | 0 | 0 | — | 12 | 0 | 0 | 0% |
| 2026-06-21 14:17 UTC | dsv4-flash | dsv4-pro | 6 | 0 | 0 | — | 6 | 0 | 0 | 0% |
| 2026-06-21 19:46 UTC | dsv4-flash | dsv4-pro | 4 | 0 | 0 | — | 4 | 0 | 0 | 0% |
| 2026-06-21 20:59 UTC | dsv4-flash | dsv4-pro | 1 | 0 | 0 | — | 1 | 0 | 0 | 0% |
| 2026-06-21 21:07 UTC | dsv4-flash | dsv4-pro | 0 | 0 | 0 | — | 0 | 0 | 0 | — |
| 2026-06-22 08:09 UTC | dsv4-flash | dsv4-pro | 27 | 0 | 2 | — | 25 | 0 | [1](audit-errors.md) | 7% |
| 2026-06-22 08:27 UTC | dsv4-flash | dsv4-pro | 0 | 0 | 0 | — | 0 | 0 | 0 | — |
| 2026-06-22 10:45 UTC | dsv4-flash | dsv4-pro | 20 | 0 | 2 | — | 18 | 0 | 0 | 10% |
| 2026-06-22 13:26 UTC | dsv4-flash | dsv4-pro | 35 | 1 | 5 | — | 29 | 0 | 0 | 17% |
| 2026-06-22 14:52 UTC | dsv4-flash | dsv4-pro | 6 | 0 | 0 | 0 | 6 | 0 | 0 | 0% |
| 2026-06-22 15:58 UTC | dsv4-flash | dsv4-pro | 5 | 0 | 2 | 2 | 1 | 0 | 0 | 80% |
| 2026-06-22 19:47 UTC | dsv4-flash | dsv4-pro | 36 | 5 | 11 | 7 | 13 | 0 | 0 | 64% |
| 2026-06-22 20:10 UTC | dsv4-flash | dsv4-pro | 3 | 0 | 1 | 1 | 1 | 0 | 0 | 67% |
| 2026-06-23 08:33 UTC | dsv4-flash | dsv4-pro | 1596 | 4 | 45 | 1453 | 94 | 1465 | [1](audit-errors.md) | 94% |
| 2026-06-23 13:45 UTC | dsv4-flash | dsv4-pro | 60 | 3 | 8 | 12 | 37 | 1 | 0 | 38% |
| 2026-06-23 19:11 UTC | dsv4-flash | dsv4-pro | 46 | 3 | 11 | 10 | 22 | 1 | 0 | 52% |
| 2026-06-24 08:28 UTC | dsv4-flash | dsv4-pro | 520 | 2 | 16 | 442 | 60 | 426 | [1](audit-errors.md) | 88% |
| 2026-06-24 13:26 UTC | dsv4-flash | dsv4-pro | 61 | 4 | 11 | 17 | 29 | 1 | 0 | 52% |
| 2026-06-24 18:55 UTC | dsv4-flash | dsv4-pro | 47 | 4 | 7 | 8 | 28 | 3 | 0 | 40% |
| 2026-06-25 08:28 UTC | dsv4-flash | dsv4-pro | 562 | 2 | 17 | 504 | 39 | 492 | [1](audit-errors.md) | 93% |
| 2026-06-25 13:23 UTC | dsv4-flash | dsv4-pro | 70 | 0 | 11 | 13 | 46 | 0 | 0 | 34% |
| 2026-06-25 19:08 UTC | dsv4-flash | dsv4-pro | 45 | 1 | 9 | 11 | 24 | 1 | [1](audit-errors.md) | 47% |
| 2026-06-26 08:33 UTC | dsv4-flash | dsv4-pro | 535 | 1 | 35 | 438 | 61 | 436 | [6](audit-errors.md) | 89% |
| 2026-06-26 13:15 UTC | dsv4-flash | dsv4-pro | 55 | 4 | 13 | 7 | 31 | 1 | 0 | 44% |
| 2026-06-26 18:56 UTC | dsv4-flash | dsv4-pro | 56 | 3 | 14 | 15 | 24 | 1 | 0 | 57% |
| 2026-06-27 07:53 UTC | dsv4-flash | dsv4-pro | 16 | 0 | 1 | 0 | 15 | 0 | 0 | 6% |
| 2026-06-27 12:12 UTC | dsv4-flash | dsv4-pro | 6 | 0 | 1 | 0 | 5 | 0 | 0 | 17% |
| 2026-06-27 18:11 UTC | dsv4-flash | dsv4-pro | 14 | 2 | 4 | 1 | 7 | 0 | 0 | 50% |
| 2026-06-28 08:26 UTC | dsv4-flash | dsv4-pro | 16 | 0 | 1 | 1 | 14 | 0 | 0 | 12% |
