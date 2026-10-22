# Gauntlet: ds-smoke

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8 | alone | 11 | 18% (5–48) | 50% (24–76) | 70% (48–85) | 1/1 | 1 | $72,529 |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## Wrong numbers that match a known shortcut

| Shortcut | Times |
|---|---|
| ignore_social_security_torpedo | 1 |
| ignore_capital_gains_stacking | 1 |

## Costliest wrong decisions by a model alone (video candidates)

- **g-how_much-1** (or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8): plan gives up $134,445; costs $134,445
- **g-senior_phaseout-1** (or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8): picked B; best was C; costs $72,529
- **g-first_rmd-1** (or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8): picked C; best was A; costs $7,161
- **g-torpedo_irmaa-1** (or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8): picked C; best was A; costs $3,704

