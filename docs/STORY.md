# The PlannerBench story (the brief every page follows)

Owner: Peyton Thalman. This file is the single source for the site's arc, voice and headline numbers.
If a page and this file disagree, fix one of them; never let them drift.

## Who reads this

1. **A normal person** who clicked a tweet: "I tested whether AI gets retirement math right." No finance or AI
   background, five minutes, leaves at the first wall of jargon. They want one answer: *can I trust it?*
2. **A hiring manager at an AI company**: ten minutes, wants to see judgment, rigor, honesty about limits,
   and what Peyton personally decided versus what AI agents did.
3. **An AI agent** reading on someone's behalf. It gets the same content as plain text (no JavaScript).

Target: both human readers score it 10/10 for "easy to follow the story."

## The one sentence

AI is great at simple retirement questions; on real ones it depends heavily on which AI you ask; a trusted
calculator rescues some models but not others; and when you tell it something wrong, the cheap ones almost never
notice and even the best miss some, which is now the biggest gap.

## Why I made this (the opening, first person)

- I'm a financial advisor; I meet most people by knocking on their door ("door to door as a financial advisor").
  The employer is never named.
- My dad became a financial advisor in 1999; watching him take care of people is why I do this. He passed away in
  2017. (From peytonthalman.com/about; one or two sentences at most, not sentimental.)
- More and more people tell me they get their financial advice from ChatGPT. When I ask how they know it's right,
  they Google it, and the top result is another AI's answer.
- So I wrote the questions planners work through every week, built an answer key I could prove, and tested the
  models.
- How it was built: I directed AI coding agents (mostly Claude Code) to build and run all of it; I made the calls
  (what to test, what counts as right, when to spend, what to publish). Say this plainly. Because AI did much of the
  work, independent checks matter, and the site shows them (see "How I checked").

## A straight answer for a normal person (home page, near the top)

"Should I trust AI with my retirement questions?" Plain answer, in this spirit:
- For a single, well-known rule (this year's tax bracket, an IRA withdrawal), the best AIs are almost always right.
- For your whole situation (taxes, Social Security and Medicare at once), it depends a lot on which AI. Free or
  cheap ones get most of these wrong; the very best got nearly all right in my newest test.
- The biggest risk isn't the math. It's what you type in. Cheap AIs almost never notice if a number you gave them can't
  be right, and even the best miss about one in four; they hand back a confident answer anyway. Double-check your inputs, and take big decisions to a
  professional.

## The four findings (order is fixed; each links to its page)

1. **Simple questions: almost always right.** Claude Sonnet 5.5 and Haiku 5.5: about 97% on one-rule questions
   (first test, October 2026). Page: AI on its own (alone.html).
2. **Real-life questions: it depends which AI.** When several rules meet in one household, scores spread out. In
   the first test (October): Sonnet 37%, Haiku 17% on questions stacking several rules; many models made the same
   misreading of a rule new in 2025 (the senior deduction). In the newer, harder set (November, 11 models):
   GPT-6.1 Sol 98%, Claude Sonnet 5.5 62%, most cheap models under 30%. The two tests used different settings
   (October: high reasoning effort, long replies; November: low effort, 4,000-token replies); say that where both
   appear and never put the two in one chart. Page: AI on its own (alone.html).
3. **Give it a calculator it can trust.** I turned the answer key into a calculator AI can call (the planning
   engine; an MCP server). Page: With a calculator (calculator.html). Beats, in order:
   - Hand it the right number and it argues: Claude Haiku 5.5 on the 50 hardest first-test questions went from 40%
     alone to 62% with a calculator that returned only the number; in most misses it overruled the calculator with
     its own wrong rule.
   - Show it the rule and it listens: when the calculator also showed the rule and the IRS form line, 100% (50/50);
     on 50 held-back questions nobody tuned against, 96% (48/50; both misses overruled it again).
   - A cheap model can catch up: in the November set, DeepSeek V4.1 Flash went from 29% to 79% with the calculator,
     ahead of Claude Sonnet 5.5 alone (62%) at about a fifteenth of the cost per right answer.
   - Honest catch: three other cheap models called the calculator and still got under 10%; the best model
     (GPT-6.1 Sol) gained nothing.
   - Whole-household decisions (formerly "the Gauntlet"): with the calculator, all three models tested got all 11
     right (one per family plus a trap), including DeepSeek, which got 2 of 11 alone. Small sample.
   - Leave a fact out: with the calculator, DeepSeek asked for the missing fact 9 of 10 times.
   - Try it yourself: it plugs into Claude and ChatGPT (chat.html).
4. **Tell it something wrong: the best catch most, the cheap ones almost none. This is the biggest open gap.**
   (Not "most won't notice": 7 of 11 models caught at least half. "Best" = catching without false alarms;
   Gemini 3.8 Flash caught 92% but flagged half the valid files.) 30 client files, one planted
   mistake each (a retiree who is 14, spending ten times what the family owns, a contribution over the legal limit).
   GPT-6.1 Sol caught 80% and Claude Sonnet 5.5 73% with almost no false alarms; three cheap models caught 1–3% and gave a confident
   number 81–93% of the time. Some noticed the problem and answered anyway. Every model was worst at a plausible
   amount that's over a legal limit. Page: Wrong facts (wrong-facts.html).

Then: **What this means for you** (three plain bullets), **How I checked** (method.html), **How I built it**
(built.html: phase 1 October, phase 2 November).

## Names (use these; never the old ones in public text)

| Say | Not |
|---|---|
| the first test (October 2026) | v1 |
| the newer, harder set (November 2026) | v2, hard tier |
| whole-household decisions | the Gauntlet |
| the planning engine / the calculator | MoneyGuide, MCP server (except one technical aside) |
| AI on its own · With a calculator · Wrong facts · How I checked · How I built it | Results · With tools · Bad inputs · Method |
| the 50 hardest questions from the first test / the 42 questions in the newer set | "50 hard questions" and "42 hard questions" side by side unexplained |
| cheap / free models, the best models | frontier, mid-tier, open weights (unless explained once) |

## Voice and page rules

- First person, plain words, short sentences. Headline = the finding, as a sentence a normal person understands.
- Every page opens with a 2–3 sentence plain answer, then one concrete example, then the evidence.
- Explain any term the first time it appears (IRA, Roth conversion, RMD, Medicare premium surcharge), or use a plain
  word instead. Keep technical detail (intervals, p-values, hosts, fp8, token budgets) inside `<details>` toggles
  labeled "For the technical reader" or "How this was run".
- Big tables go behind toggles; show the 3–5 rows that tell the story first.
- Every claim is scoped: which models, which test, how many questions. No "AI" when you mean "these 11 models".
- Limits are stated where the claim is made, briefly, not saved for the end.
- Every number in the text comes from a data file. Numbers typed as text are logged in web/data/system.json with
  their source.
- House style (peytonthalman.com): white paper, ink, hairlines, Newsreader headlines, Geist text, no pills,
  no shadows, no italics in headlines.
