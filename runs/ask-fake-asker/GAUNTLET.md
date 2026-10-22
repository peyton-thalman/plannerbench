# Gauntlet: ask-fake-asker

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| fake | alone | 69 | 100% (95–100) | 100% (95–100) | 100% (97–100) | 0/0 | 0 | – |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## Ask first: did it ask before advising?

One decisive fact was left out of each question (every reasonable guess grades wrong; src/gauntlet_ask.py). A scripted client answers questions on that fact's topic and never volunteers.

| Model | Engine | Asked | Asked any question | Got the missing fact | Great when it got the fact | Great when it guessed | Questions per reply |
|---|---|---|---|---|---|---|---|
| fake | alone | 69 | 100% (95–100) | 100% (95–100) | 100% (95–100) | – | 1.0 |

