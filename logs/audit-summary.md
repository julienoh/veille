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
| 2026-06-28 12:19 UTC | dsv4-flash | dsv4-pro | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0% |
| 2026-06-28 18:10 UTC | dsv4-flash | dsv4-pro | 10 | 1 | 1 | 0 | 8 | 0 | 0 | 20% |
| 2026-06-29 09:54 UTC | dsv4-flash | dsv4-pro | 488 | 5 | 16 | 380 | 87 | 362 | [7](audit-errors.md) | 82% |
| 2026-06-29 14:50 UTC | dsv4-flash | dsv4-pro | 42 | 3 | 5 | 14 | 20 | 0 | 0 | 52% |
| 2026-06-29 19:07 UTC | dsv4-flash | dsv4-pro | 39 | 0 | 10 | 12 | 17 | 1 | [1](audit-errors.md) | 56% |
| 2026-06-30 08:34 UTC | dsv4-flash | dsv4-pro | 580 | 2 | 18 | 498 | 62 | 483 | [5](audit-errors.md) | 89% |
| 2026-06-30 13:11 UTC | dsv4-flash | dsv4-pro | 56 | 4 | 12 | 10 | 30 | 0 | 0 | 46% |
| 2026-06-30 19:00 UTC | dsv4-flash | dsv4-pro | 67 | 3 | 9 | 17 | 38 | 0 | 0 | 43% |
| 2026-07-01 08:52 UTC | dsv4-flash | dsv4-pro | 663 | 7 | 24 | 559 | 73 | 544 | [2](audit-errors.md) | 89% |
| 2026-07-01 13:37 UTC | dsv4-flash | dsv4-pro | 60 | 1 | 12 | 11 | 36 | 2 | 0 | 40% |
| 2026-07-01 19:02 UTC | dsv4-flash | dsv4-pro | 59 | 5 | 12 | 12 | 30 | 0 | 0 | 49% |
| 2026-07-02 08:16 UTC | dsv4-flash | dsv4-pro | 522 | 5 | 18 | 450 | 49 | 438 | [4](audit-errors.md) | 91% |
| 2026-07-02 13:02 UTC | dsv4-flash | dsv4-pro | 63 | 6 | 11 | 8 | 38 | 2 | 0 | 40% |
| 2026-07-02 18:40 UTC | dsv4-flash | dsv4-pro | 37 | 2 | 7 | 10 | 18 | 0 | 0 | 51% |
| 2026-07-03 08:15 UTC | dsv4-flash | dsv4-pro | 617 | 0 | 28 | 530 | 59 | 523 | [3](audit-errors.md) | 90% |
| 2026-07-03 13:01 UTC | dsv4-flash | dsv4-pro | 60 | 2 | 10 | 7 | 41 | 1 | 0 | 32% |
| 2026-07-03 18:17 UTC | dsv4-flash | dsv4-pro | 29 | 2 | 5 | 7 | 15 | 0 | 0 | 48% |
| 2026-07-04 07:51 UTC | dsv4-flash | dsv4-pro | 17 | 0 | 0 | 1 | 16 | 0 | 0 | 6% |
| 2026-07-04 12:11 UTC | dsv4-flash | dsv4-pro | 11 | 0 | 1 | 0 | 10 | 0 | 0 | 9% |
| 2026-07-04 18:07 UTC | dsv4-flash | dsv4-pro | 13 | 1 | 2 | 1 | 9 | 0 | 0 | 31% |
| 2026-07-05 08:06 UTC | dsv4-flash | dsv4-pro | 15 | 0 | 1 | 2 | 12 | 0 | 0 | 20% |
| 2026-07-05 12:22 UTC | dsv4-flash | dsv4-pro | 8 | 0 | 0 | 0 | 8 | 0 | 0 | 0% |
| 2026-07-05 18:10 UTC | dsv4-flash | dsv4-pro | 7 | 0 | 0 | 1 | 6 | 0 | 0 | 14% |
| 2026-07-06 09:05 UTC | dsv4-flash | dsv4-pro | 63 | 0 | 9 | 9 | 45 | 0 | 0 | 29% |
| 2026-07-06 14:31 UTC | dsv4-flash | dsv4-pro | 51 | 4 | 6 | 9 | 32 | 0 | [1](audit-errors.md) | 37% |
| 2026-07-06 19:01 UTC | dsv4-flash | dsv4-pro | 51 | 4 | 4 | 9 | 34 | 0 | 0 | 33% |
| 2026-07-07 08:29 UTC | dsv4-flash | dsv4-pro | 1461 | 8 | 50 | 1272 | 131 | 1291 | [15](audit-errors.md) | 91% |
| 2026-07-07 13:23 UTC | dsv4-flash | dsv4-pro | 72 | 4 | 14 | 14 | 40 | 1 | 0 | 44% |
| 2026-07-07 19:06 UTC | dsv4-flash | dsv4-pro | 57 | 5 | 16 | 9 | 27 | 1 | 0 | 53% |
| 2026-07-08 07:34 UTC | dsv4-flash | dsv4-pro | 489 | 3 | 23 | 414 | 49 | 404 | [1](audit-errors.md) | 90% |
| 2026-07-08 12:26 UTC | dsv4-flash | dsv4-pro | 60 | 4 | 12 | 13 | 31 | 1 | 0 | 48% |
| 2026-07-08 18:23 UTC | dsv4-flash | dsv4-pro | 65 | 4 | 10 | 14 | 37 | 0 | 0 | 43% |
| 2026-07-09 08:33 UTC | dsv4-flash | dsv4-pro | 511 | 3 | 15 | 437 | 56 | 418 | [1](audit-errors.md) | 89% |
| 2026-07-09 13:52 UTC | dsv4-flash | dsv4-pro | 70 | 6 | 9 | 15 | 40 | 1 | [1](audit-errors.md) | 43% |
| 2026-07-09 18:53 UTC | dsv4-flash | dsv4-pro | 54 | 0 | 10 | 14 | 30 | 2 | [1](audit-errors.md) | 44% |
| 2026-07-10 08:28 UTC | dsv4-flash | dsv4-pro | 295 | 0 | 10 | 227 | 58 | 206 | [1](audit-errors.md) | 80% |
| 2026-07-10 13:16 UTC | dsv4-flash | dsv4-pro | 46 | 2 | 13 | 9 | 22 | 1 | 0 | 52% |
| 2026-07-10 18:25 UTC | dsv4-flash | dsv4-pro | 47 | 4 | 12 | 13 | 18 | 1 | [1](audit-errors.md) | 62% |
| 2026-07-11 07:15 UTC | dsv4-flash | dsv4-pro | 165 | 0 | 7 | 133 | 25 | 121 | 0 | 85% |
| 2026-07-11 11:57 UTC | dsv4-flash | dsv4-pro | 15 | 1 | 2 | 1 | 11 | 0 | 0 | 27% |
| 2026-07-11 17:59 UTC | dsv4-flash | dsv4-pro | 12 | 0 | 1 | 0 | 11 | 0 | 0 | 8% |
| 2026-07-12 07:32 UTC | dsv4-flash | dsv4-pro | 11 | 0 | 0 | 0 | 11 | 0 | 0 | 0% |
| 2026-07-12 12:03 UTC | dsv4-flash | dsv4-pro | 6 | 0 | 0 | 2 | 4 | 0 | 0 | 33% |
| 2026-07-12 18:03 UTC | dsv4-flash | dsv4-pro | 6 | 0 | 1 | 1 | 4 | 0 | 0 | 33% |
| 2026-07-13 08:21 UTC | dsv4-flash | dsv4-pro | 359 | 1 | 12 | 317 | 29 | 304 | [1](audit-errors.md) | 92% |
