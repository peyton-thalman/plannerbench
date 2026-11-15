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
noticed and even GPT-6.1 Sol and Claude Sonnet 5.5 missed about one in four or five (20–27%).

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
- Say what was tested, not whom to trust: "On the one-rule questions I tested, Claude Sonnet 5.5 and Haiku 5.5 were right
  about 97% of the time" (this year's tax bracket, an IRA withdrawal), never "trust the best AIs on a single rule".
- For your whole situation (taxes, Social Security and Medicare at once), it depends a lot on which AI. Free or
  cheap ones get most of these wrong; the very best got nearly all right in my newest test.
- Check what you type in. Say what was measured, not "the biggest risk": in my tests, three cheap models almost never
  questioned an impossible fact, and even Sol and Sonnet missed 20–27%; they handed back a confident answer anyway.
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
   - Honest catch: three other cheap models called the calculator and still got under 10%; the highest scorer
     (GPT-6.1 Sol) gained nothing.
   - Whole-household decisions (formerly "the Gauntlet"): with the calculator, all three models tested got all 11
     right (one per family plus a trap), including DeepSeek, which got 2 of 11 alone. Small sample.
   - Leave a fact out: with the calculator, DeepSeek asked for the missing fact 9 of 10 times.
   - Try it yourself: it plugs into Claude and ChatGPT (chat.html).
4. **Tell it something wrong: Sol and Sonnet catch most, three cheap models almost none.** (Say "three cheap models", not
   "cheap models": DeepSeek V4.1 Flash caught 61% and GLM 5.3 Flash 40%. "Caught" = recognized the mistake and stopped and asked, giving no number.)
   (Not "most won't notice": 7 of 11 models caught at least half. "Best" = catching without false alarms;
   Gemini 3.8 Flash caught 92% but flagged half the valid files.) 30 client files, one planted
   mistake each (a retiree who is 14, spending ten times what the family owns, a contribution over the legal limit).
   GPT-6.1 Sol caught 80% and Claude Sonnet 5.5 73% with almost no false alarms; three cheap models caught 1–3% and gave a confident
   number 81–93% of the time. Some noticed the problem and answered anyway. Every model was worst at a plausible
   amount that's over a legal limit. Page: Wrong facts (wrong-facts.html).

Home page order (structural pass, 2026-11-15; aim: half the old length, now about 720 visible words, was about 1,090):
1. Headline + a plain answer scoped to what was tested ("On the one-rule questions I tested, the two Claude models were
   right about 97% of the time. On questions where several rules meet, the scores depended heavily on which AI…").
2. The bottom-line box: the definitions of "one rule" and "several rules at once"; three bullets (one rule; several rules at
   once, naming Sol, Terra and Sonnet, with GPT-6 Luna's 17%; impossible facts); the How-sure line as a one-sentence
   verification boundary (outside coverage: the first test's tax answers, by PolicyEngine-US; everything else: two
   separately written programs agreeing; still awaiting a person: CPA sign-off, a spot-check of the AI judge); the
   "About ChatGPT" line (the regular ChatGPT app uses GPT-6 Luna, a different, cheaper model than GPT-6.1 Sol; this run
   went through OpenAI's Codex app with code and web off, in small batches, so it's close to but not the same as typing
   into ChatGPT); What to do this week.
3. **The story in 60 seconds**: the problem (door-to-door advisor; clients ask ChatGPT), what I built (answer key from the
   planning engine, rechecked by separate programs, then the questions; AI agents built it, I made the calls), the strongest
   result (calculator test 1: 40% → 62% → 100% on 50, 96% on 50 held back), the limits (small samples, an AI judge, no CPA).
4. **Three results**: It depends which AI (Sol vs Sonnet, Terra named, vs cheap; GPT-6 Luna on its own line with its setup note) · Hand it
   the answer and it argues (Haiku 40% → 100%; catch: DeepSeek rose, three cheap models didn't) · It accepts impossible
   facts (caught = recognized + stopped and asked).
5. **What I decided**: build the checker before the questions ("a second program, written without seeing the first, agreed
   on all 4,000 test households", in words, no "cleanroom" or "4,000 / 4,000"); fix the calculator's reply, not the
   prompt; keep secret test questions; have another company's model audit it and publish the 12 errors. Link to How I built it.
6. **The experiments** map, headed "If you want to dig in, here's every test", columns Test · When · What it asked · How
   many · Which AIs, linking to each page, with one plain settings sentence ("October and November used different
   settings, so compare within a test, not across") and the price groups in one line.
7. Next → AI on its own.
Plain definitions at first use on Home: "one rule", "several rules at once", "answer key", "planning engine",
"held-back questions", "AI judge", "planted mistakes".
Not on Home any more: "Why I made this" (the dad line moved to How I built it's lede), "How to read the numbers", the
trust paragraph, the reading list. Verification language: "within $1" / "within $2", never "to the dollar".

Experiment names (use the same words on Home's map, page eyebrows and anchors):
First test (Oct) · Newer, harder set (Nov) · GPT-6 Luna through Codex (Nov) · Calculator test 1: number vs rule (Oct) ·
Calculator test 2: who it rescues (Nov) · Calculator test 3: whole-household decisions (Oct) · Wrong facts (Nov).

Wrong facts uses two named measures everywhere: **recognized the mistake** (the reply named it) and **stopped and asked**
(gave no number, asked for the fact instead). **Caught** = both. The four outcome buckets are the 2×2 of those measures
(Caught it · Noticed, answered anyway · Declined for another reason · Missed it, answered anyway), plus Ran out of room.

Page rules from the structural pass: each finding page opens with its own 2–3 sentence answer and doesn't re-summarize
the other findings or re-explain verification (one line + a link to How I checked at most). The first thing after the
plain answer is prose or a table of 5 rows or fewer; full tables sit behind `<details>` labeled "All models and columns
(for the detail-minded)". How I built it: decisions first, then mistakes caught, who did what; no restated findings.

Reading order, the nav, and every page's bottom "Next" link: home → AI on its own → With a calculator → Wrong facts →
How I built it → How I checked → home. (Decisions come before method: hiring managers were finding them last.)

## Names (use these; never the old ones in public text)

| Say | Not |
|---|---|
| the first test (October 2026) | v1 |
| the newer, harder set (November 2026) | v2, hard tier |
| whole-household decisions | the Gauntlet |
| the planning engine / the calculator | MoneyGuide, MCP server (except one technical aside) |
| AI on its own · With a calculator · Wrong facts · How I built it · How I checked | Results · With tools · Bad inputs · Method |
| the 50 hardest questions from the first test / the 42 questions in the newer set | "50 hard questions" and "42 hard questions" side by side unexplained |
| top-priced / mid-priced / cheap and free (price groups); name the models when ranking | "the best models" as a group (who is best depends on the measure: highest on the hard set is Sol, then Terra; best at catching mistakes without false alarms is Sol, then Sonnet), frontier, mid-tier, open weights |
| GPT-6 Luna through Codex (the model on my ChatGPT subscription) at first mention per page, then GPT-6 Luna | "ChatGPT" for the model or the result ("ChatGPT" only for the app itself) |
| a projected $X less after-tax wealth over 25 years (a simulation, not a real household) | "costs the household $X" |

## Voice and page rules

- First person, plain words, short sentences. Headline = the finding, as a sentence a normal person understands.
- Every page opens with a 2–3 sentence plain answer, then one concrete example, then the evidence.
- Explain any term the first time it appears (IRA, Roth conversion, RMD, Medicare premium surcharge), or use a plain
  word instead. Keep technical detail (intervals, p-values, hosts, fp8, token budgets) inside `<details>` toggles
  labeled "For the technical reader" or "How this was run".
- Big tables go behind toggles; show the 3–5 rows that tell the story first.
- Every claim is scoped: which models, which test, how many questions. No "AI" when you mean "these 11 models".
- Limits are stated where the claim is made, briefly, not saved for the end.
- Percentages round half up everywhere (app.js Math.round; charts use the same rule), so 1/40 shows as 3% on every page.
- Every number in the text comes from a data file. Numbers typed as text are logged in web/data/system.json with
  their source.
- House style (peytonthalman.com): white paper, ink, hairlines, Newsreader headlines, Geist text, no pills,
  no shadows, no italics in headlines.
