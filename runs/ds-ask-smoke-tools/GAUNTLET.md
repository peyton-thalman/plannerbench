# Gauntlet: ds-ask-smoke-tools

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8 | with | 10 | 90% (60–98) | 90% (60–98) | 90% (70–97) | 0/0 | 0 | – |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## Ask first: did it ask before advising?

One decisive fact was left out of each question (every reasonable guess grades wrong; src/gauntlet_ask.py). A scripted client answers questions on that fact's topic and never volunteers.

| Model | Engine | Asked | Asked any question | Got the missing fact | Great when it got the fact | Great when it guessed | Questions per reply |
|---|---|---|---|---|---|---|---|
| or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8 | with | 10 | 90% (60–98) | 90% (60–98) | 100% (70–100) | 0% (0–79) | 0.9 |

## With the engine: why wrong answers were wrong

Override (the engine showed the right answer and the model went against it): **0**; possible override (matched on unnamed plans, may be a coincidence): 0; mistranslated (wrong inputs to the tools): 0; no call got through: 0; never called the tools: 0.

### Tool plumbing

| Model | Replies | Tool calls | Malformed (not valid JSON) | Rejected by the engine | Replies with no tool call |
|---|---|---|---|---|---|
| or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8 | 10 | 31 | 0 | 0 | 0 |

