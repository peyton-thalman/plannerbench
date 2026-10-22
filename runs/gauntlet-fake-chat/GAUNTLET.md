# Gauntlet: gauntlet-fake-chat

| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |
|---|---|---|---|---|---|---|---|---|
| fake | with | 77 | 100% (95–100) | 100% (95–100) | 100% (97–100) | 7/7 | 0 | – |

Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.

## With the engine: why wrong answers were wrong

Override (the engine showed the right answer and the model went against it): **0**; possible override (matched on unnamed plans, may be a coincidence): 0; mistranslated (wrong inputs to the tools): 0; no call got through: 0; never called the tools: 0.

### Tool plumbing

| Model | Replies | Tool calls | Malformed (not valid JSON) | Rejected by the engine | Replies with no tool call |
|---|---|---|---|---|---|
| fake | 77 | 216 | 13 | 0 | 4 |

