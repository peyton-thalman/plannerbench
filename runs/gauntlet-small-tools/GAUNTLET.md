# Gauntlet: gauntlet-small-tools

2 replies failed at the API and aren't scored (rerun the same command to retry them).

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | with | 11 | 100% (74–100) | 100% (72–100) | 100% (84–100) | 1/1 | 0 | – |
| claude-sonnet-5-5 | with | 11 | 100% (74–100) | 100% (72–100) | 100% (84–100) | 1/1 | 0 | – |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## With the engine: why wrong answers were wrong

Override (the engine showed the right answer and the model went against it): **0**; possible override (matched on unnamed plans, may be a coincidence): 0; mistranslated (wrong inputs to the tools): 0; never called the tools: 0.

