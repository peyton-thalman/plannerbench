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
calculator rescues some models but not others; and when you tell it something wrong, three cheap models almost never
noticed and even the best two missed about one in four or five (20–27%).

Home page's one-sentence version (names names): the best AI I tested, GPT-6.1 Sol, got 98% of my hardest questions
right and Claude Sonnet 5.5 got 62%; all five cheap and free models scored under 30%, and three of them almost never
noticed a fact that couldn't be true. "Best" = right most often; on wrong facts, catching the most without false alarms.

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
- Check what you type in. Say what was measured, not "the biggest risk": in my tests, three cheap models almost never
  questioned an impossible fact, and even the best two missed 20–27%; they handed back a confident answer anyway.
  (Don't say "the math isn't the problem": one model said $70,200 exceeds $798,000.)

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
4. **Tell it something wrong: the best catch most, three cheap models almost none.** (Say "three cheap models", not
   "cheap models": DeepSeek V4.1 Flash caught 61% and GLM 5.3 Flash 40%. "Caught" = named the mistake and gave no number.)
   (Not "most won't notice": 7 of 11 models caught at least half. "Best" = catching without false alarms;
   Gemini 3.8 Flash caught 92% but flagged half the valid files.) 30 client files, one planted
   mistake each (a retiree who is 14, spending ten times what the family owns, a contribution over the legal limit).
   GPT-6.1 Sol caught 80% and Claude Sonnet 5.5 73% with almost no false alarms; three cheap models caught 1–3% and gave a confident
   number 81–93% of the time. Some noticed the problem and answered anyway. Every model was worst at a plausible
   amount that's over a legal limit. Page: Wrong facts (wrong-facts.html).

Home page order (round 2): one-sentence answer naming names + what "best" means; why I made this; the straight answer;
"How to read the numbers" (the first test: 2,800 generated, each model asked 10–15 per task = 140–210; the newer set:
42 hard questions + 30 client files, 11 models; the answer key; the calculator = the answer key as a tool an AI can
call, not usable on the site, chat demo private); four finding cards (one number, model, test, catch beside it);
why you can trust the numbers (AI-built, so independent programs; audit found and fixed 12 errors, public; pending CPA
is an extra check, the independent programs already agree within $1–2); ends with **Before you trust an AI with a
retirement number: three things**. Verification language: "within $1" / "within $2", never "to the dollar".

Reading order and every page's bottom "Next" link: home → AI on its own → With a calculator → Wrong facts →
How I checked → How I built it.

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
