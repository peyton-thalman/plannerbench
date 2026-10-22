# Gauntlet: gauntlet-small

20 replies failed at the API and aren't scored (rerun the same command to retry them).

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | alone | 11 | 36% (15–65) | 70% (40–89) | 70% (48–85) | 1/1 | 0 | $7,161 |
| claude-sonnet-5-5 | alone | 10 | 70% (40–89) | 67% (35–88) | 67% (44–84) | 1/1 | 0 | – |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## Wrong numbers that match a known shortcut

| Shortcut | Times |
|---|---|
| phaseout_once | 1 |
| ignore_capital_gains_stacking | 1 |

## Costliest wrong decisions by a model alone (video candidates)

- **g-how_much-1** (claude-haiku-5-5): plan gives up $26,002; costs $26,002
- **g-first_rmd-1** (claude-haiku-5-5): picked C; best was A; costs $7,161
- **g-torpedo_irmaa-1** (claude-haiku-5-5): picked B; best was A; costs $4,154; numbers via N1: ignore_capital_gains_stacking

