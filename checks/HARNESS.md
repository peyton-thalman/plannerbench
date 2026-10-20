# Harness check: direct API vs. OpenRouter

The same model asked the same questions both ways. Pass means no significant difference (exact McNemar p > 0.05).

| Model | Shared questions | Direct | OpenRouter | Flipped (direct right only / OpenRouter right only) | p | Result |
|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 140 | 77% [70%–83%] | 77% [70%–83%] | 6 / 6 | 1.000 | PASS |

Runs: `live-high-10x1` (direct) and `or-5models-15x1` (OpenRouter).
