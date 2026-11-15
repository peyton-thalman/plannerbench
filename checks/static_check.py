"""Static check: can someone (or a crawler) with no JavaScript read every number on the site?

Fetches each page's raw HTML, exactly as served, and checks that:
  - the headline numbers are already in the HTML and match the graded data (leaderboard/, web/data/)
  - no slot app.js would fill is still empty or "—", no table body is empty, and app.js isn't loaded
  - every page links its Markdown twin, and every .md, llms.txt and llms-full.txt is served and non-empty
  - every link in llms.txt resolves
  - the old page names redirect to the new ones (live: the HTTP redirect; local copy: site/vercel.json)

Usage: .venv/bin/python -I checks/static_check.py [http://localhost:4173]
  (serve the baked site first: python3 -m http.server 4173 --directory site)
"""
import json
import math
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT = Path(__file__).parent.parent
LIVE = "https://plannerbench.vercel.app"
PAGES = ["index", "results", "alone", "wrong-facts", "calculator", "method", "built", "chat", "report", "replay", "agent"]
REDIRECTS = {"v2": "wrong-facts", "gauntlet": "calculator"}


def load(name):
    p = ROOT / "leaderboard" / f"{name}.json"
    return json.loads((p if p.exists() else ROOT / "web" / "data" / f"{name}.json").read_text())


def pct(x):  # the same rounding as app.js (Math.round: halves go up)
    return f"{math.floor(x * 100 + 0.5)}%"


def span(xs):  # the same as app.js span(): "73–80%", or "73%" when both round the same
    lo, hi = pct(min(xs)), pct(max(xs))
    return lo if lo == hi else f"{lo[:-1]}–{hi}"


def expected():
    """What each page must say, worked out here from the data rather than read back from the page."""
    models, tools, meta, system = load("models"), load("tools"), load("meta"), load("system")
    lead = next(m for m in models if m["model"] == "claude-sonnet-5-5")
    st = tools["hard"]["stages"]
    cr = system["cleanroom"]
    v2 = load("v2"); v2m = {m["name"]: m for m in v2["models"]}
    # Home is the short story (2026-11-15): one number per finding, each a link into Results. The test table and the
    # "second program agreed on all" line moved to Methods, so they are checked there.
    luna = load("luna")
    home = {"single": pct(lead["single_step_accuracy"]),
            "tools_from": pct(st[0]["accuracy"]), "tools_to": pct(st[-1]["accuracy"]),
            "a_best_missed": span([1 - v2m["GPT-6.1 Sol"]["bad"]["caught"]["rate"], 1 - v2m["Claude Sonnet 5.5"]["bad"]["caught"]["rate"]])}
    cheap = [m for m in v2["models"] if m.get("tier") == "cheap"]
    text = {
        "index": [pct(v2m["GPT-6.1 Sol"]["hard"]["rate"]), pct(v2m["Claude Sonnet 5.5"]["hard"]["rate"]), pct(luna["hard"]["rate"]),
                  # home says "cheap and free models scored under 30%", so the check only passes while all of them did
                  "under 30%" if all(m["hard"]["rate"] < 0.3 for m in cheap) else "(home says all cheap models under 30%; they aren't)",
                  'href="results.html#one-rule"', 'href="results.html#several-rules"', 'href="results.html#calculator"', 'href="results.html#wrong-facts"'],
        "results": [pct(v2m["GPT-6.1 Sol"]["hard"]["rate"]), pct(lead["single_step_accuracy"])] + [f"{s['right']}/{s['questions']}" for s in st],
        "alone": [m["name"] for m in models] + [pct(m["accuracy"]) for m in models] + [pct(lead["stacked_accuracy"])],
        "calculator": [f"{s['right']}/{s['questions']}" for s in st],
        "method": [f"{meta['questions']:,}", f"{cr['agree']:,}" if cr["agree"] == cr["of"] else "(methods says all agree; they don't)"],
    }
    return home, text


class Page(HTMLParser):
    """Collects what the checks need from raw HTML: fill slots, table bodies, scripts, links."""

    def __init__(self, src):
        super().__init__(convert_charrefs=True)
        self.slots, self.stack, self.scripts, self.links = [], [], [], []
        self.feed(src)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        if tag == "link":
            self.links.append(a)
        if tag in ("br", "img", "meta", "link", "input", "hr", "source", "wbr", "col"):
            return
        key = a.get("data-k") or a.get("data-c") or a.get("data-v")
        self.stack.append([tag, key, ""])

    def handle_endtag(self, tag):
        while self.stack:
            t, key, txt = self.stack.pop()
            if key:
                self.slots.append((key, re.sub(r"\s+", " ", txt).strip()))
            if self.stack:
                self.stack[-1][2] += txt
            if t == tag:
                break

    def handle_data(self, d):
        if self.stack:
            self.stack[-1][2] += d


def fetch(url, follow=True):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.headers
    except urllib.error.HTTPError as e:
        return e.code, "", e.headers


def main(base):
    base = base.rstrip("/")
    fails, notes = [], []
    ok = lambda cond, msg: (notes if cond else fails).append(msg)
    home, text = expected()

    for name in PAGES:
        code, src, _ = fetch(f"{base}/{name}.html")
        if code != 200:
            fails.append(f"{name}.html: HTTP {code}")
            continue
        p = Page(src)
        empty = [k for k, v in p.slots if v in ("", "—", "–")]
        ok(not empty, f"{name}.html: fill slots filled in raw HTML" + (f" (empty: {', '.join(empty)})" if empty else ""))
        ok(not re.search(r"<tbody>\s*</tbody>", src), f"{name}.html: no empty table body")
        ok(not any(s.split("?")[0].endswith("app.js") for s in p.scripts), f"{name}.html: app.js not loaded")
        ok(any(l.get("rel") == "alternate" and l.get("type") == "text/markdown" and l.get("href") == f"/{name}.md" for l in p.links),
           f"{name}.html: links its Markdown twin /{name}.md")
        ok("Loading replays" not in src, f"{name}.html: nothing stuck on 'Loading'")
        if name == "index":
            got = dict(p.slots)
            for k, want in home.items():
                ok(got.get(k) == want, f"index.html: data-k={k} is {want!r} in raw HTML" + ("" if got.get(k) == want else f" (found {got.get(k)!r})"))
            ok('"@type": "Dataset"' in src, "index.html: JSON-LD Dataset present")
        for want in text.get(name, []):
            ok(want in src, f"{name}.html: says {want!r}")
        mcode, md, mh = fetch(f"{base}/{name}.md")
        ok(mcode == 200 and md.startswith("# ") and len(md) > 500, f"{name}.md: served, non-empty, starts with a heading")
        if name == "index":
            for k, want in home.items():
                ok(want in md, f"index.md: says {want!r}")

    for f in ("llms.txt", "llms-full.txt", "robots.txt", "sitemap.xml"):
        code, body, _ = fetch(f"{base}/{f}")
        ok(code == 200 and len(body) > 50, f"{f}: served and non-empty")
        if f == "llms.txt":
            ok(body.startswith("# ") and "\n> " in body, "llms.txt: H1 and summary blockquote")
            links = re.findall(r"\]\((https?://[^)]+)\)", body)
            bad = []
            for u in links:
                local = u.replace(LIVE, base) if u.startswith(LIVE) else None
                if local and fetch(local)[0] != 200:
                    bad.append(u)
            ok(links and not bad, f"llms.txt: all {len(links)} links resolve" + (f" (broken: {', '.join(bad)})" if bad else ""))
        if f == "llms-full.txt":
            ok(all(v in body for v in home.values()), "llms-full.txt: has the home page's numbers")

    # Redirects: live, the server answers with one; a local copy can only show the config that will be deployed.
    code, _, h = fetch(f"{base}/v2.html", follow=False)
    if code in (301, 302, 307, 308):
        for old, new in REDIRECTS.items():
            for src in (f"/{old}.html", f"/{old}"):
                c, _, hh = fetch(f"{base}{src}", follow=False)
                loc = (hh.get("Location") or "") if hh else ""
                ok(c in (301, 308) and loc.rstrip("/").endswith(f"/{new}.html"), f"redirect {src} → /{new}.html (HTTP {c})")
    else:
        cfg = ROOT / "site" / "vercel.json"
        rules = json.loads(cfg.read_text()).get("redirects", []) if cfg.exists() else []
        have = {(r["source"], r["destination"]) for r in rules if r.get("permanent")}
        for old, new in REDIRECTS.items():
            for src in (f"/{old}.html", f"/{old}"):
                ok((src, f"/{new}.html") in have, f"site/vercel.json: permanent redirect {src} → /{new}.html")

    for n in notes:
        print(f"[PASS] {n}")
    for f in fails:
        print(f"[FAIL] {f}")
    print("PASS: every page reads without JavaScript" if not fails else f"FAIL: {len(fails)} problem(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else LIVE)
