# Synthèse pipeline — 30 derniers jours

Rétention glissante 30 jours. Append en bas (le plus récent en bas).

- `Trouvés` : articles frais après filtrage URL/date.
- `RN` / `RL` : retenus en read_now / read_later (entrent dans le digest).
- `Arch` : tout ce qui ne passe pas le filtre decision (skim, archive, dédup).
- `Dédup` : articles rétrogradés par la phase 2.
- `Err` : erreurs survenues (cliquable → audit-errors.md).
- `Retenue%` : (RN + RL) / Trouvés.

| Date UTC | Filtrage | Synthèse | Trouvés | RN | RL | Arch | Dédup | Err | Retenue% |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-06-19 20:20 UTC | dsv4-flash | dsv4-pro | 0 | 0 | 0 | 0 | 0 | 0 | — |
| 2026-06-20 09:20 UTC | dsv4-flash | dsv4-pro | 10 | 0 | 0 | 10 | 0 | 0 | 0% |
| 2026-06-20 14:10 UTC | dsv4-flash | dsv4-pro | 9 | 0 | 0 | 9 | 0 | 0 | 0% |
| 2026-06-20 19:41 UTC | dsv4-flash | dsv4-pro | 4 | 0 | 0 | 4 | 0 | 0 | 0% |
| 2026-06-21 09:54 UTC | dsv4-flash | dsv4-pro | 12 | 0 | 0 | 12 | 0 | 0 | 0% |
| 2026-06-21 14:17 UTC | dsv4-flash | dsv4-pro | 6 | 0 | 0 | 6 | 0 | 0 | 0% |
| 2026-06-21 19:46 UTC | dsv4-flash | dsv4-pro | 4 | 0 | 0 | 4 | 0 | 0 | 0% |
| 2026-06-21 20:59 UTC | dsv4-flash | dsv4-pro | 1 | 0 | 0 | 1 | 0 | 0 | 0% |
| 2026-06-21 21:07 UTC | dsv4-flash | dsv4-pro | 0 | 0 | 0 | 0 | 0 | 0 | — |
| 2026-06-22 08:09 UTC | dsv4-flash | dsv4-pro | 27 | 0 | 2 | 25 | 0 | [1](audit-errors.md) | 7% |
| 2026-06-22 08:27 UTC | dsv4-flash | dsv4-pro | 0 | 0 | 0 | 0 | 0 | 0 | — |
