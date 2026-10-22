# Gauntlet: ds-ask-smoke

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8 | alone | 5 | 40% (12–77) | 40% (12–77) | 70% (40–89) | 0/0 | 0 | $134,445 |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## Ask first: did it ask before advising?

One decisive fact was left out of each question (every reasonable guess grades wrong; src/gauntlet_ask.py). A scripted client answers questions on that fact's topic and never volunteers.

| Model | Engine | Asked | Asked any question | Got the missing fact | Great when it got the fact | Great when it guessed | Questions per reply |
|---|---|---|---|---|---|---|---|
| or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8 | alone | 5 | 100% (57–100) | 100% (57–100) | 40% (12–77) | – | 2.4 |

## Wrong numbers that match a known shortcut

| Shortcut | Times |
|---|---|
| flat_24pct | 1 |

## Costliest wrong decisions by a model alone (video candidates)

- **g-how_much-1** (or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8): plan gives up $134,445; costs $134,445; numbers via N1: flat_24pct
- **g-senior_phaseout-1** (or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8): picked A; best was C; costs $26,852

