"""Build the v2 charts and site pages from the graded results.

  .venv/bin/python v2/build_site.py

Reads v2/results/summary.json (from v2/grade.py) and REPORT.md. Writes:
  v2/results/charts/*.svg     the three charts (also used by REPORT.md)
  site/charts/*.svg           the same files for the site
  site/data/v2.json           the numbers the v2 page shows
  site/v2.html                the v2 leaderboard
  site/report.html            REPORT.md as a page
in the shared site style (v1 scores and data are untouched). The nav lives in each page; NAV here must match it.
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
V2 = ROOT / "v2"
SITE = ROOT / "site"
S = json.loads((V2 / "results" / "summary.json").read_text())
MODELS = S["models"]
# Validated with the dataviz palette checker against the site's paper (#faf8f5): all pass; amber is under 3:1 contrast,
# so every amber mark carries a visible label and each chart has a table beside it.
TIER = {"frontier": "#1f8a6b", "mid": "#c2571a", "cheap": "#2a78d6"}
TIER_NAME = {"frontier": "Frontier", "mid": "Mid-tier", "cheap": "Cheap / open weights"}
OUT = {"caught": ("#1f8a6b", "Caught the mistake and asked"), "flagged_but_answered": ("#d99a1e", "Noticed it, answered anyway"),
       "silent_number": ("#b5402f", "Missed it, answered anyway"), "declined_other_reason": ("#9a958c", "Wouldn't answer, for another reason")}
INK, MUTED, RULE, PAPER = "#16181c", "#4d525b", "#e7e8e8", "#ffffff"
FONT = 'font-family="Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"'
e = html.escape


HEADLINE = ("Given client notes with one planted error, three of five cheap open-weight models answered "
            "confidently 81–93% of the time and caught 1–3%. The best models caught 73% with almost no false "
            "alarms. With the planning engine as a tool, a cheap model went from 29% to 79% on hard questions.")

def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{e(label)}" {FONT}>'
            f'<rect width="{w}" height="{h}" fill="{PAPER}"/>{body}</svg>\n')


def text(x, y, s, size=12, fill=MUTED, anchor="start", weight=400):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{e(str(s))}</text>'


def chart_catch():
    """Catch rate against false-alarm rate: one dot per model. Up and to the left is better."""
    W, H, L, R, T, B = 760, 500, 64, 150, 56, 56
    pw, ph = W - L - R, H - T - B
    X = lambda v: L + pw * v
    Y = lambda v: T + ph * (1 - v)
    b = [text(L, 22, "Caught the planted mistake vs. refused a note that was fine", 15, INK, weight=600),
         text(L, 40, "Each dot is one model. Up and to the left is better.", 12)]
    for v in (0, .25, .5, .75, 1):
        b.append(f'<line x1="{L}" x2="{L + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{RULE}"/>' + text(L - 10, Y(v) + 4, f"{v:.0%}", anchor="end"))
        b.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{T + ph}" stroke="{RULE}"/>' + text(X(v), T + ph + 20, f"{v:.0%}", anchor="middle"))
    b.append(text(L + pw / 2, H - 10, "Refused a note that was fine (false alarm)", 12, anchor="middle"))
    b.append(f'<text transform="translate(16 {T + ph / 2:.0f}) rotate(-90)" font-size="12" fill="{MUTED}" text-anchor="middle">Caught the planted mistake</text>')
    pts = sorted([(m["bad"]["false_alarm"]["rate"], m["bad"]["caught"]["rate"], m) for m in MODELS if m["bad"]], key=lambda p: -p[1])
    placed = []
    dots = [(X(fa), Y(c)) for fa, c, _ in pts]
    for fa, c, m in pts:
        x, y = X(fa), Y(c)
        # start the label to the right of every dot in the same small cluster, so no name sits under a dot
        lx_ = max(dx for dx, dy in dots if abs(dy - y) < 18 and abs(dx - x) < 40) + 12
        ly, step = y + 4, (-14 if c < 0.10 else 14)   # near the floor, stack names upward off the axis
        while any(abs(ly - py) < 14 and abs(lx_ - px) < 130 for px, py in placed):
            ly += step
        placed.append((lx_, ly))
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{TIER[m["tier"]]}" stroke="{PAPER}" stroke-width="2"><title>{e(m["name"])}: caught {c:.0%}, false alarms {fa:.0%}</title></circle>')
        b.append(text(lx_, ly, m["name"], 12, INK))
    ly = T + 14
    for t, col in TIER.items():
        b.append(f'<circle cx="{L + pw + 20}" cy="{ly - 4}" r="6" fill="{col}"/>' + text(L + pw + 32, ly, TIER_NAME[t], 12, MUTED))
        ly += 20
    return svg(W, H, "".join(b), "Catch rate against false-alarm rate on the bad-inputs track, one dot per model")


def chart_outcomes():
    """What each model did with a note that had a mistake planted in it: four outcomes that add to 100%."""
    ms = sorted([m for m in MODELS if m["bad"]], key=lambda m: (-m["bad"]["caught"]["rate"], m["bad"]["silent_number"]["rate"]))
    W, L, R, T, row = 760, 170, 24, 112, 30
    H = T + row * len(ms) + 16
    pw = W - L - R
    b = [text(16, 24, "30 client notes, each with one mistake planted. What did each model do?", 16, INK, weight=600),
         text(16, 44, "Green is what you want. Red is a confident answer built on a wrong fact.", 12.5)]
    for n, (k, (col, name)) in enumerate(OUT.items()):
        lx, ly = 16 + (n % 2) * 300, 62 + (n // 2) * 20
        b.append(f'<rect x="{lx}" y="{ly}" width="12" height="12" rx="2" fill="{col}"/>' + text(lx + 18, ly + 10.5, name, 12.5))
    for n, m in enumerate(ms):
        y = T + n * row
        b.append(text(L - 10, y + 15, m["name"], 12.5, INK, "end"))
        x = L
        for k, (col, name) in OUT.items():
            v = m["bad"][k]["rate"]
            w = pw * v
            if w > 0.5:
                b.append(f'<rect x="{x + 1:.1f}" y="{y}" width="{max(0.5, w - 2):.1f}" height="20" rx="3" fill="{col}"><title>{e(m["name"])}: {e(name)} {v:.0%}</title></rect>')
                if v >= 0.07:
                    b.append(text(x + w / 2, y + 14, f"{v:.0%}", 11, "#ffffff" if k != "flagged_but_answered" else INK, "middle", 600))
            x += w
    return svg(W, H, "".join(b), "What each model did with a note that had a mistake planted in it")


def chart_false_alarms():
    """How often each model refused a note that was fine. One series, sorted, value at the end of each bar."""
    ms = sorted([m for m in MODELS if m["bad"]], key=lambda m: (m["bad"]["false_alarm"]["rate"], -m["bad"]["caught"]["rate"]))
    W, L, R, T, row = 760, 170, 60, 64, 26
    H = T + row * len(ms) + 12
    pw = W - L - R
    b = [text(16, 24, "The other way to fail: refusing a note that was fine", 16, INK, weight=600),
         text(16, 44, "Share of 40 correct notes where the model said it couldn't answer. Shorter is better.", 12.5)]
    for n, m in enumerate(ms):
        y = T + n * row
        v = m["bad"]["false_alarm"]["rate"]
        b.append(text(L - 10, y + 14, m["name"], 12.5, INK, "end"))
        b.append(f'<rect x="{L}" y="{y}" width="{pw}" height="18" rx="3" fill="#f1f1ef"/>')
        if v > 0:
            b.append(f'<rect x="{L}" y="{y}" width="{max(3, pw * v):.1f}" height="18" rx="3" fill="{INK}"><title>{e(m["name"])}: refused {v:.0%} of correct notes</title></rect>')
        b.append(text(L + pw * v + 8, y + 14, f"{v:.0%}", 12.5, INK, weight=600))
    return svg(W, H, "".join(b), "Share of correct notes each model refused to answer")


def chart_tools():
    """Hard tier: each model alone and, where run, with the engine. One axis, two marks per row."""
    ms = sorted([m for m in MODELS if m["hard"]], key=lambda m: -max(m["hard"]["rate"], (m["hard_tools"] or {"rate": 0})["rate"]))
    W, L, R, T, row = 760, 170, 60, 84, 30
    H = T + row * len(ms) + 40
    pw = W - L - R
    X = lambda v: L + pw * v
    b = [text(16, 24, "Hard questions answered right: on its own, then with the planning engine", 16, INK, weight=600),
         text(16, 44, "42 questions where several rules meet. Hollow dot: the model alone. Solid dot: with the engine to call.", 12.5),
         f'<circle cx="{L + 6}" cy="60" r="6" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>' + text(L + 18, 64, "Alone", 12.5),
         f'<circle cx="{L + 76}" cy="60" r="6" fill="{INK}"/>' + text(L + 88, 64, "With the engine", 12)]
    for v in (0, .25, .5, .75, 1):
        b.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T - 6}" y2="{T + row * len(ms)}" stroke="{RULE}"/>' + text(X(v), T + row * len(ms) + 18, f"{v:.0%}", anchor="middle"))
    for n, m in enumerate(ms):
        y = T + n * row + 12
        a, t = m["hard"]["rate"], m["hard_tools"]
        col = TIER[m["tier"]]
        b.append(text(L - 10, y + 4, m["name"], 12, INK, "end"))
        if t:
            b.append(f'<line x1="{X(a):.1f}" x2="{X(t["rate"]):.1f}" y1="{y}" y2="{y}" stroke="{col}" stroke-width="2"/>')
            b.append(f'<circle cx="{X(t["rate"]):.1f}" cy="{y}" r="7" fill="{col}" stroke="{PAPER}" stroke-width="2"><title>{e(m["name"])} with the engine: {t["rate"]:.0%} of {t["n"]} questions</title></circle>')
            lab = f'{t["rate"]:.0%}' + (f' (on {t["n"]})' if t["n"] < 42 else "")
            b.append(text(X(max(a, t["rate"])) + 13, y + 4, lab, 12, INK, weight=600))
            if abs(t["rate"] - a) > 0.06:
                b.append(text(X(min(a, t["rate"])) - 13, y + 4, f"{a:.0%}" if a < t["rate"] else lab, 12, MUTED, "end"))
        else:
            b.append(text(X(a) + 13, y + 4, f"{a:.0%}", 12, MUTED))
        b.append(f'<circle cx="{X(a):.1f}" cy="{y}" r="6" fill="{PAPER}" stroke="{col}" stroke-width="2"><title>{e(m["name"])} alone: {a:.0%}</title></circle>')
    return svg(W, H, "".join(b), "Hard-tier accuracy by model, alone and with the engine")


# ---- pages ----------------------------------------------------------------------------------------------------------

NAV = [('results.html', 'Results'), ('v2.html', 'Bad inputs'), ('gauntlet.html', 'With tools'), ('method.html', 'Method'), ('built.html', 'How I built it')]


def page(title, desc, current, main, name):
    nav = "\n      ".join(f'<a href="{h}"{" aria-current=\"page\"" if h == current else ""}>{t}</a>' for h, t in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)} · PlannerBench</title>
<meta name="description" content="{e(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&family=Newsreader:ital,opsz,wght@0,6..72,400..500;1,6..72,400..500&display=swap">
<link rel="stylesheet" href="styles.css?v=18">
</head>
<body data-page="{name}">
<header class="nav">
  <div class="wrap nav-row">
    <a class="wordmark" href="./">PlannerBench</a>
    <nav aria-label="Pages">
      {nav}
    </nav>
  </div>
</header>

<main>
{main}
</main>

<footer class="foot">
  <div class="wrap foot-row">
    <span>PlannerBench · 2026 rules · <a href="report.html">Report</a> · <a href="chat.html">In the chat</a> · <a href="replay.html">Replays</a> · <a href="https://peytonthalman.com">peytonthalman.com</a></span>
    <span>Decision support, not advice. Answers follow IRS, SSA and CMS publications; nothing here is tax or investment advice.</span>
  </div>
</footer>
</body>
</html>
"""


def pc(x):
    return "–" if x is None else f"{x:.0%}"


def cell(d, low=None):
    """A score cell in the site's style: value, bar, 95% band."""
    if not d or d.get("rate") is None:
        return '<td><span class="ci">not run</span></td>'
    r, lo, hi = d["rate"], d["lo"], d["hi"]
    cls = "cell low" if (low is not None and low(r)) else "cell"
    return (f'<td><div class="{cls}"><span class="v">{r:.0%}</span><div class="track"><div class="band-ci" style="left:{lo:.1%};width:{hi - lo:.1%}"></div>'
            f'<div class="fill" style="width:{r:.1%}"></div></div><span class="ci">{lo:.0%}–{hi:.0%}</span></div></td>')


def model_cell(m, runs):
    return f'<td class="model">{e(m["name"])}<span class="via">{TIER_NAME[m["tier"]].lower()} · {runs}</span></td>'


def v2_page():
    bad = sorted([m for m in MODELS if m["bad"]], key=lambda m: -m["bad"]["net"])
    rows = "".join(
        f'<tr>{model_cell(m, f"{m["bad"]["reps"]:.0f} run{"s" if m["bad"]["reps"] > 1 else ""} per note")}{cell(m["bad"]["caught"], lambda r: r < .5)}'
        f'{cell(m["bad"]["silent_number"])}{cell(m["bad"]["false_alarm"])}{cell(m["bad"]["clean_correct"])}'
        f'<td class="overall">{100 * m["bad"]["net"]:+.0f}</td></tr>' for m in bad)
    hard = sorted([m for m in MODELS if m["hard"]], key=lambda m: -m["hard"]["rate"])
    hrows = ""
    for m in hard:
        h, t = m["hard"], m["hard_tools"]
        tc = cell(t) if t else '<td><span class="ci">not run</span></td>'
        if t and t["n"] < 42:
            tc = tc.replace('</span></div></td>', f' · {t["n"]} questions</span></div></td>')
        hrows += (f'<tr>{model_cell(m, f"{h["reps"]:.0f} run{"s" if h["reps"] > 1 else ""} per question")}{cell(h)}<td class="cost">{h["truncated"]:.0%}</td>{tc}'
                  f'<td class="cost">{"–" if not t else f"{t["call_rate"]:.0%}"}</td>'
                  f'<td class="cost">{"–" if h["cost_per_correct"] is None else f"${1000 * h["cost_per_correct"]:.2f}"}</td>'
                  f'<td class="cost">{"–" if not t or t["cost_per_correct"] is None else f"${1000 * t["cost_per_correct"]:.2f}"}</td></tr>')
    fams = list(next(m for m in MODELS if m["hard"])["hard"]["by_family"])
    frows = "".join(f'<tr>{model_cell(m, "alone")}' + "".join(f'<td class="cost">{pc(m["hard"]["by_family"].get(f, {}).get("rate"))}</td>' for f in fams) + "</tr>" for m in hard)
    types = ["transposed", "impossible_age", "spending", "conflict", "over_limit"]
    trows = "".join(f'<tr>{model_cell(m, "caught, by kind of problem")}' + "".join(f'<td class="cost">{pc(m["bad"]["by_type"][t]["caught"]["rate"])}</td>' for t in types) + "</tr>" for m in bad)
    best = bad[0]
    j = S["judge_check"]
    main = f"""  <section class="page-head wrap">
    <p class="eyebrow">PlannerBench v2 · 2026-11-14</p>
    <h1>The math got easy. Catching a bad input didn’t.</h1>
    <p class="lede">People give AI the wrong facts all the time: a mistyped balance, the wrong birth year, a guess at what they spend. Then they make decisions from the answer. So I planted one mistake in each of 30 client notes and watched what {len(MODELS)} models did.</p>
    <div class="example">
      <p class="label">One example</p>
      <p>The note said a retired school administrator with a $785,000 IRA was born in 2012, and asked for this year’s required withdrawal. One model replied:</p>
      <blockquote>“Priya will be 14 years old throughout 2026 … no required minimum distribution is required. ANSWER: 0”</blockquote>
      <p>With her real birth year the answer is $34,279. The model saw the age and didn’t question it.</p>
    </div>
    <p class="cta"><a class="btn primary" href="report.html">Read the report</a></p>
  </section>

  <section class="band">
    <div class="wrap">
      <div class="section-head">
        <h2>Who notices when the client’s facts can’t be right?</h2>
        <p class="sub">Each note had one planted mistake: two digits swapped, an impossible birth year, spending far beyond what the household has, two facts that conflict, or an amount over a legal limit. A model could answer with a number or say it needed more information.</p>
      </div>
      <figure class="chart-card"><div class="chart"><img src="charts/outcomes.svg" alt="What each model did with a note that had a mistake planted in it, as shares that add to 100%; the full table below has the same numbers" style="width:100%;height:auto"></div></figure>
      <p class="takeaway"><b>What it shows.</b> The best models caught about three mistakes in four. Three of the five cheapest gave a confident answer more than eight times in ten. Every model was worst at the same kind: a believable amount that is over a legal limit.</p>
      <figure class="chart-card value-card"><div class="chart"><img src="charts/false_alarms.svg" alt="Share of correct notes each model refused to answer; the full table below has the same numbers" style="width:100%;height:auto"></div></figure>
      <p class="takeaway"><b>What it shows.</b> A model can’t win by refusing everything. Each mistaken note had a correct twin, plus ten notes that look odd but are fine. The two Gemini models refused half or more of those, mostly because they didn’t know this year’s tax law.</p>
      <details class="fine wide">
        <summary>Full table, with 95% intervals</summary>
        <div class="table-wrap">
          <table class="scores">
            <thead><tr><th scope="col">Model</th><th scope="col">Caught the mistake</th><th scope="col">Missed it, answered anyway</th><th scope="col">Refused a correct note</th><th scope="col">Correct notes answered right</th><th scope="col" class="r">Net (caught − refused)</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        <p class="table-note">Caught = named the planted mistake and gave no number. Bars show the score; the shaded band is the 95% interval. Whether a reply named the mistake is judged by a second model ({e(j["judge"].split("/")[-1].split("@")[0])}); the other columns are rule-based.</p>
      </details>
      <details class="fine wide">
        <summary>Caught, by kind of mistake</summary>
        <div class="table-wrap">
          <table class="scores">
            <thead><tr><th scope="col">Model</th><th scope="col" class="r">Swapped digits</th><th scope="col" class="r">Impossible age</th><th scope="col" class="r">Spending can’t fit</th><th scope="col" class="r">Facts conflict</th><th scope="col" class="r">Over a legal limit</th></tr></thead>
            <tbody>{trows}</tbody>
          </table>
        </div>
      </details>
    </div>
  </section>

  <section class="wrap section">
    <div class="section-head">
      <h2>Harder questions, and whether a tool rescues a cheap model</h2>
      <p class="sub">42 new questions where several rules meet: a Roth conversion that changes Medicare premiums two years later, an inherited IRA, a widow’s first tax year, state tax on top of federal. Each answer comes from the planning engine and is matched to the dollar by a second engine written separately.</p>
    </div>
    <figure class="chart-card"><div class="chart"><img src="charts/hard_tools.svg" alt="Hard questions answered right by each model, alone and with the engine; the full table below has the same numbers" style="width:100%;height:auto"></div></figure>
    <p class="takeaway"><b>What it shows.</b> With the engine to call, one cheap model (DeepSeek) went from 29% to 79%, past a far pricier model working alone. Three other cheap models called the engine and still got the answer wrong, so the tool only helps a model that can use it.</p>
    <details class="fine wide">
      <summary>Full table, with cost per right answer</summary>
      <div class="table-wrap">
        <table class="scores">
          <thead><tr><th scope="col">Model</th><th scope="col">Alone</th><th scope="col" class="r">Ran out of room</th><th scope="col">With the engine</th><th scope="col" class="r">Called the engine</th><th scope="col" class="r">Cost per 1,000 right, alone</th><th scope="col" class="r">With the engine</th></tr></thead>
          <tbody>{hrows}</tbody>
        </table>
      </div>
    </details>
    <details class="fine wide">
      <summary>By kind of question, models alone</summary>
      <div class="table-wrap">
        <table class="scores">
          <thead><tr><th scope="col">Model</th>{"".join(f'<th scope="col" class="r">{e(f.replace("_", " "))}</th>' for f in fams)}</tr></thead>
          <tbody>{frows}</tbody>
        </table>
      </div>
    </details>
    <details class="fine">
      <summary>How these were run</summary>
      <p>Every model through OpenRouter, pinned to one host, data collection off, one user message and no system prompt. Reasoning effort low and a 4,000-token reply limit for all (Mistral Small with reasoning off). Total spend ${S["spend"]["spent_usd"]:.2f} against a $5 cap, which is why the most expensive models have one run per item. Small samples: read the intervals, not the ranks.</p>
    </details>
  </section>
"""
    return page("v2: bad inputs and the hard tier", "PlannerBench v2: does a model notice when a client's facts are wrong, and does a planning engine rescue a cheap model on hard retirement questions?", "v2.html", main, "v2")


def inline(s):
    s = e(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", lambda m: f'<img src="charts/{Path(m[2]).name}" alt="{m[1]}" style="width:100%;height:auto">', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m[2] if m[2].startswith("http") else "https://github.com/peyton-thalman/plannerbench/blob/v2/" + m[2]}">{m[1]}</a>', s)
    return s


def markdown(md):
    """Enough Markdown for REPORT.md: headings, paragraphs, lists, quotes, fenced code, tables, images."""
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        l = lines[i]
        if not l.strip():
            i += 1
        elif l.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append('<pre class="rp-raw" style="white-space:pre-wrap;background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:1rem;font-family:var(--mono)">' + e("\n".join(lines[i + 1:j])) + "</pre>")
            i = j + 1
        elif l.startswith("#"):
            n = len(l) - len(l.lstrip("#"))
            tag = {1: "h1", 2: "h2", 3: "h3"}.get(n, "h3")
            out.append(f"<{tag}>{inline(l[n:].strip())}</{tag}>")
            i += 1
        elif l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            out.append('<div class="table-wrap"><table class="scores"><thead><tr>' + "".join(f'<th scope="col">{inline(c)}</th>' for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f'<td{" class=\"model\"" if n == 0 else ""}>{inline(c)}</td>' for n, c in enumerate(r)) + "</tr>" for r in body) + "</tbody></table></div>")
        elif l.startswith(">"):
            q = []
            while i < len(lines) and lines[i].startswith(">"):
                q.append(lines[i][1:].strip())
                i += 1
            out.append('<blockquote class="aside" style="margin-top:0">' + "".join(f"<p>{inline(p)}</p>" for p in "\n".join(q).split("\n\n") if p.strip()) + "</blockquote>")
        elif re.match(r"(- |\d+\. )", l):
            ordered = not l.startswith("- ")
            items = []
            while i < len(lines) and (re.match(r"(- |\d+\. )", lines[i]) or (lines[i].startswith("  ") and items)):
                if re.match(r"(- |\d+\. )", lines[i]):
                    items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
        else:
            p = []
            while i < len(lines) and lines[i].strip() and not re.match(r"(#|\||>|```|- |\d+\. )", lines[i]):
                p.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(p))}</p>")
    return "\n".join(out)


def report_page():
    md = (ROOT / "REPORT.md").read_text()
    title = md.splitlines()[0].lstrip("# ").strip()
    body = markdown("\n".join(md.splitlines()[1:]))
    main = f"""  <section class="page-head wrap">
    <p class="eyebrow">PlannerBench v2 · report</p>
    <h1>{inline(title)}</h1>
  </section>
  <section class="wrap section report" style="padding-top:0">
    <style>
      .report {{ max-width: 52rem; display: grid; gap: 1.1rem; }}
      .report h2 {{ font-size: var(--step-2); margin-top: 2rem; max-width: none; }}
      .report h3 {{ margin-top: 1rem; }}
      .report ul, .report ol {{ margin: 0; padding-left: 1.25rem; display: grid; gap: 0.4rem; }}
      .report .scores {{ min-width: 34rem; font-size: 0.9375rem; }}
      .report .scores td {{ padding: 0.6rem 0.75rem 0.6rem 0; }}
      .report blockquote p + p {{ margin-top: 0.6rem; }}
      .report a {{ color: var(--accent); }}
    </style>
{body}
  </section>
"""
    return page("Report: " + title, "The PlannerBench v2 report: bad inputs, the hard tier and tool use, with method, results, failure examples and limits.", "report.html", main, "report")


def main():
    charts = V2 / "results" / "charts"
    charts.mkdir(exist_ok=True)
    (charts / "catch_vs_false_alarm.svg").write_text(chart_catch())
    (charts / "outcomes.svg").write_text(chart_outcomes())
    (charts / "false_alarms.svg").write_text(chart_false_alarms())
    (charts / "hard_tools.svg").write_text(chart_tools())
    (SITE / "charts").mkdir(exist_ok=True)
    for f in charts.glob("*.svg"):
        shutil.copy(f, SITE / "charts" / f.name)
    (SITE / "data" / "v2.json").write_text(json.dumps({k: S[k] for k in ("settings", "items", "models", "tiers", "tool_effect", "judge_check", "bad_outcomes_all_models", "bad_by_type_all_models")}
                                                      | {"headline": HEADLINE, "spent_usd": S["spend"]["spent_usd"]}, indent=1) + "\n")
    (SITE / "v2.html").write_text(v2_page())
    if (ROOT / "REPORT.md").exists():
        (SITE / "report.html").write_text(report_page())
    print("site built")


if __name__ == "__main__":
    main()
