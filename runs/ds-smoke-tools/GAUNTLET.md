# Gauntlet: ds-smoke-tools

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8 | with | 11 | 100% (74–100) | 100% (72–100) | 100% (84–100) | 1/1 | 0 | – |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## With the engine: why wrong answers were wrong

Override (the engine showed the right answer and the model went against it): **0**; possible override (matched on unnamed plans, may be a coincidence): 0; mistranslated (wrong inputs to the tools): 0; no call got through: 0; never called the tools: 0.

### Tool plumbing

| Model | Replies | Tool calls | Malformed (not valid JSON) | Rejected by the engine | Replies with no tool call |
|---|---|---|---|---|---|
| or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8 | 11 | 30 | 0 | 0 | 0 |

## For a human look: assumed amounts not in the question

- g-senior_phaseout-1 (or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8): 27,753

