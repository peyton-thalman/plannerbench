# Gauntlet: ask-fake-guesser

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| fake | alone | 69 | 0% (0–5) | 51% (39–62) | 7% (4–13) | 0/0 | 0 | $17,958 |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## Ask first: did it ask before advising?

One decisive fact was left out of each question (every reasonable guess grades wrong; src/gauntlet_ask.py). A scripted client answers questions on that fact's topic and never volunteers.

| Model | Engine | Asked | Asked any question | Got the missing fact | Great when it got the fact | Great when it guessed | Questions per reply |
|---|---|---|---|---|---|---|---|
| fake | alone | 69 | 0% (0–5) | 0% (0–5) | – | 0% (0–5) | 0.0 |

## Wrong numbers that match a known shortcut

| Shortcut | Times |
|---|---|
| ignore_social_security_torpedo | 4 |
| no_phaseout | 4 |
| ignore_senior_deduction | 3 |
| flat_15pct | 2 |
| flat_12pct | 2 |
| phaseout_once | 1 |
| flat_24pct | 1 |
| ignore_capital_gains_stacking | 1 |
| ignore_niit | 1 |
| flat_22pct | 1 |

## Costliest wrong decisions by a model alone (video candidates)

- **g-claim_age-2** (fake): picked B,C; best was C; costs $244,758
- **g-claim_age-1** (fake): picked A; best was C; costs $186,765
- **g-claim_age-4** (fake): picked C; best was A; costs $164,842
- **g-senior_phaseout-7** (fake): picked A,B,C; best was A; costs $97,522; numbers via N1: flat_15pct, N2: phaseout_once
- **g-senior_phaseout-2** (fake): picked A,B,C; best was A; costs $94,620; numbers via N2: no_phaseout
- **g-senior_phaseout-4** (fake): picked A,B,C; best was C; costs $84,637; numbers via N2: no_phaseout
- **g-senior_phaseout-1** (fake): picked A,B,C; best was C; costs $72,529; numbers via N2: no_phaseout
- **g-torpedo_irmaa-6** (fake): picked A,B,C; best was A; costs $67,278
- **g-how_much-3** (fake): plan gives up $63,752; costs $63,752
- **g-torpedo_irmaa-5** (fake): picked A,B,C; best was C; costs $57,742

