"""Build the v2 charts, data and report page from the graded results.

  .venv/bin/python v2/build_site.py

Reads v2/results/summary.json (from v2/grade.py) and REPORT.md. Writes:
  v2/results/charts/*.svg     the three charts (also used by REPORT.md)
  web/charts/*.svg            the same files for the site
  web/data/v2.json            the numbers the wrong-facts page quotes
  web/report.html             REPORT.md as a page, with the nav and stylesheet link copied from web/index.html
web/wrong-facts.html is a hand-edited page like the others (this script no longer writes it). Then run
src/bake_site.py to render web/ into site/.
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
V2 = ROOT / "v2"
SITE = ROOT / "web"  # page sources; src/bake_site.py renders them into site/
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

def shared_head_nav(current):
    """The nav block and stylesheet link of web/index.html, so the report page always matches the hand-edited pages."""
    idx = (SITE / "index.html").read_text()
    nav = idx[idx.index("<nav"):idx.index("</nav>") + len("</nav>")]
    nav = nav.replace(' aria-current="page"', "")
    nav = re.sub(r'(<a href="%s")' % re.escape(current), r'\1 aria-current="page"', nav, count=1)
    # The Human/Agent switch links "Human" to the page itself.
    nav = re.sub(r'(<a class="mode-human" href=")[^"]*(")', r'\g<1>%s\2' % current, nav)
    css = re.search(r'<link rel="stylesheet" href="styles\.css[^"]*">', idx)[0]
    return nav, css


def page(title, desc, current, main, name):
    nav, css = shared_head_nav(current)
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
{css}
</head>
<body data-page="{name}">
<header class="nav">
  <div class="wrap nav-row">
    <a class="wordmark" href="./">PlannerBench</a>
    {nav}
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
    if (ROOT / "REPORT.md").exists():
        (SITE / "report.html").write_text(report_page())
    print("site built")


if __name__ == "__main__":
    main()
