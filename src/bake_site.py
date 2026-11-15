"""Bake the site: render every page in web/ with headless Chrome and write plain, readable HTML to site/.

  .venv/bin/python src/bake_site.py

web/ holds the page sources; app.js fills their numbers, tables and charts from web/data/*.json in the browser.
This script serves web/ on a local port, lets Chrome run app.js on each page, and saves the finished DOM, so the
deployed pages need no JavaScript (app.js is dropped; replay.html keeps replay.js for its pickers, but its first
replay is already written into the page). It also writes, from the baked pages:

  site/<page>.md        a Markdown twin of every page (tables kept, charts as tables of their numbers)
  site/llms.txt         the llms.txt map (llmstxt.org) linking to the twins
  site/llms-full.txt    the whole site as one Markdown document
  site/robots.txt, site/sitemap.xml, site/vercel.json (redirects for the old page names, Markdown headers)

It fails, and leaves the previous site/ alone, if a slot app.js fills is still empty or "—", or a table body is
empty. Stdlib only. Set CHROME to use another Chrome binary.
"""
import concurrent.futures
import functools
import html
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
SITE = ROOT / "site"
BASE = "https://plannerbench.vercel.app"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
# Reading order: the nav, then the footer pages. agent.html is the agent-mode landing page itself.
ORDER = ["index", "alone", "wrong-facts", "calculator", "method", "built", "chat", "report", "replay", "agent"]
LABEL = {"index": "Home", "alone": "AI on its own", "wrong-facts": "Wrong facts", "calculator": "With a calculator",
         "method": "How I checked", "built": "How I built it", "chat": "Try it in Claude or ChatGPT", "report": "Report", "replay": "Replays", "agent": "Agent mode"}
OPTIONAL = {"replay", "agent"}  # listed under "Optional" in llms.txt
REDIRECTS = {"v2": "wrong-facts", "gauntlet": "calculator", "results": "alone"}  # old page name → new
KEEP_SCRIPTS = {"replay.js"}  # scripts a baked page may still load (interactive, not filling)
SKIP_COPY = {"app.js"}  # web/ files the baked site doesn't need


# ---- render -----------------------------------------------------------------------------------------------------------

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(WEB)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def render(url, profile, width=1280):
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=20000", f"--window-size={width},1000",
           "--hide-scrollbars", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
           f"--user-data-dir={profile}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode or "<html" not in r.stdout:
        raise RuntimeError(f"Chrome failed on {url}: exit {r.returncode}\n{r.stderr[-2000:]}")
    return r.stdout


# ---- a small DOM, from html.parser --------------------------------------------------------------------------------------

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.children, self.parent = tag, dict(attrs or {}), [], parent

    def cls(self):
        return self.attrs.get("class", "").split()

    def iter(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.iter()

    def text(self):
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def find(self, tag):
        return next((n for n in self.iter() if n.tag == tag), None)


class Tree(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node("#root")
        self.feed(src)
        self.close()

    def handle_starttag(self, tag, attrs):
        n = Node(tag, [(k, v or "") for k, v in attrs], self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, [(k, v or "") for k, v in attrs], self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(src):
    return Tree(src).root


# ---- checks on a baked page -------------------------------------------------------------------------------------------

def fill_ids():
    """Every element id app.js or replay.js writes into."""
    ids = set()
    for js in ("app.js", "replay.js"):
        src = (WEB / js).read_text()
        ids |= set(re.findall(r"(?:getElementById|\$)\('([\w-]+)'\)", src))
        ids |= set(re.findall(r"querySelector\('#([\w-]+)", src))
    return ids


def check(name, root, ids):
    bad = []
    blank = lambda n: re.sub(r"\s+", "", n.text()) in ("", "—", "–")
    for n in root.iter():
        where = f"<{n.tag}{''.join(f' {k}={v!r}' for k, v in n.attrs.items() if k in ('id', 'data-k', 'data-c', 'data-v', 'class'))}>"
        if ("data-k" in n.attrs or "data-c" in n.attrs or "data-v" in n.attrs) and blank(n):
            bad.append(f"empty fill slot {where}")
        if n.attrs.get("id") in ids and n.tag not in ("select", "table") and blank(n) and not any(isinstance(c, Node) and c.tag == "svg" for c in n.iter()):
            bad.append(f"empty fill target {where}")
        if n.tag == "tbody" and not n.find("tr"):
            bad.append(f"empty table body in {n.parent.attrs.get('id') or 'a table'}")
        if n.tag == "select" and not n.find("option"):
            bad.append(f"empty picker {where}")
        if n.tag == "script" and n.attrs.get("src") and n.attrs["src"].split("?")[0] not in KEEP_SCRIPTS:
            bad.append(f"leftover script {n.attrs['src']}")
    body = root.find("body").text()
    for stuck in ("Loading replays", "Loading…"):
        if stuck in body:
            bad.append(f"page still says {stuck!r}")
    return [f"{name}.html: {b}" for b in bad]


# ---- HTML → Markdown ------------------------------------------------------------------------------------------------------

BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "details", "summary", "figure", "figcaption",
         "div", "section", "main", "article", "header", "footer", "nav", "aside", "blockquote", "pre", "dl", "dt", "dd", "hr",
         "form", "fieldset", "svg"}
SKIP = {"script", "style", "template", "head", "noscript", "button", "input", "option"}


def hidden(n):
    return "hidden" in n.attrs or n.attrs.get("aria-hidden") == "true" or n.tag in SKIP


def has_block(n):
    return any(isinstance(c, Node) and not hidden(c) and (c.tag in BLOCK or has_block(c)) for c in n.children)


def chart_rows(svg_root):
    """A chart's numbers: the <title> tooltip on each mark, split into item and value."""
    rows = []
    for t in svg_root.iter():
        if t.tag == "title" and t.parent is not None and t.parent.tag != "svg":
            s = re.sub(r"\s+", " ", t.text()).strip()
            item, _, value = s.partition(": ")
            rows.append((item, value) if value else (s, ""))
    return rows


def md_table(rows, head=None):
    esc = lambda s: s.replace("|", "\\|").replace("\n", " ").strip()
    if not rows and not head:
        return ""
    head = head or rows.pop(0)
    width = max(len(head), *(len(r) for r in rows)) if rows else len(head)
    pad = lambda r: [esc(c) for c in r] + [""] * (width - len(r))
    out = ["| " + " | ".join(pad(head)) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(pad(r)) + " |" for r in rows]
    return "\n".join(out)


class Markdown:
    def __init__(self, page_url):
        self.url = page_url

    def href(self, h):
        if not h or h.startswith(("mailto:", "javascript:")):
            return h
        u = urllib.parse.urljoin(self.url, h)
        return u[:-len("index.html")] if u == f"{BASE}/index.html" else u

    # inline -----------------------------------------------------------------------------------------------------------
    def inline(self, n):
        if isinstance(n, str):
            return re.sub(r"\s+", " ", n)
        if hidden(n) or n.tag == "svg":
            return ""
        t, c = n.tag, n.cls()
        if t == "br":
            return " "
        if t == "img":
            return self.image(n, inline=True)
        if t == "select":
            opt = next((o for o in n.iter() if o.tag == "option" and "selected" in o.attrs), None) or n.find("option")
            return opt.text().strip() if opt else ""
        inner = self.join(n.children)
        if t in ("b", "strong"):
            return f"**{inner.strip()}**" if inner.strip() else ""
        if t in ("em", "i"):
            return f"*{inner.strip()}*" if inner.strip() else ""
        if t == "code":
            return f"`{inner.strip()}`" if inner.strip() else ""
        if t == "a":
            h = self.href(n.attrs.get("href", ""))
            return f"[{inner.strip()}]({h})" if h and inner.strip() else inner
        if t == "span" and ({"ci", "via"} & set(c)) and inner.strip():
            return f" ({inner.strip()})"
        if t == "span" and "rp-mark" in c and inner.strip():
            return f"{inner.strip()} "
        if t == "span" and "mark" in c and inner.strip():
            return f" ({inner.strip()})"
        if t == "span" and n.parent is not None and n.parent.tag == "li" and inner.strip():
            if "no" in c:  # a line or step number inside a list item
                return f"{inner.strip()}:"
            if "amt" in c:  # the amount at the end of a list item
                return f" — {inner.strip()}"
        return inner

    def join(self, kids):
        out, prev_el = "", False
        for k in kids:
            s = self.inline(k)
            if not s:
                continue
            is_el = isinstance(k, Node)
            # Adjacent elements with no space between them (label + value spans) read as one word; split them.
            if is_el and prev_el and out and not out[-1].isspace() and not s[0].isspace() and s[0] not in ".,;:)!?%":
                out += " "
            out += s
            prev_el = is_el
        return out

    def image(self, n, inline=False):
        alt = n.attrs.get("alt", "").strip()
        src = n.attrs.get("src", "")
        if src.startswith("charts/") and src.endswith(".svg") and (WEB / src).exists():
            svg = parse((WEB / src).read_text())
            s = svg.find("svg")
            label = alt or (s.attrs.get("aria-label", "") if s else "")
            return self.chart(label, chart_rows(svg), self.href(src))
        return f"![{alt}]({self.href(src)})" if not inline else (alt and f"[image: {alt}]")

    def chart(self, label, rows, src=None):
        head = f"**Chart: {label.strip()}**" + (f" ([image]({src}))" if src else "")
        if not rows:
            return head
        return head + "\n\n" + md_table([list(r) for r in rows], ["Item", "Value"])

    # blocks -------------------------------------------------------------------------------------------------------
    def blocks(self, n):
        """Markdown blocks for a container's children: runs of inline content become paragraphs."""
        out, run = [], []

        def flush():
            s = self.join(run).strip()
            if s:
                out.append(s)
            run.clear()

        for k in n.children:
            if isinstance(k, Node) and not hidden(k) and (k.tag in BLOCK or k.tag == "img" or (k.tag != "a" and has_block(k)) or (k.tag == "a" and has_block(k))):
                flush()
                out.extend(self.block(k))
            else:
                run.append(k)
        flush()
        return out

    def block(self, n):
        t = n.tag
        if hidden(n):
            return []
        if n.attrs.get("role") == "img" or t == "svg":
            s = n if t == "svg" else n.find("svg")
            label = n.attrs.get("aria-label") or (s.attrs.get("aria-label", "") if s else "")
            return [self.chart(label, chart_rows(s) if s else [])]
        if t == "img":
            return [self.image(n)]
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            s = self.join(n.children).strip()
            return [f"{'#' * int(t[1])} {s}"] if s else []
        if t in ("p", "summary", "figcaption", "dt"):
            s = self.join(n.children).strip() if not has_block(n) else "\n\n".join(self.blocks(n))
            return [s] if s else []
        if t in ("ul", "ol"):
            items, i = [], 0
            if any(isinstance(x, Node) and "no" in x.cls() for li in n.children if isinstance(li, Node) for x in li.children):
                t = "ul"  # items carry their own numbers
            for li in n.children:
                if not isinstance(li, Node) or li.tag != "li" or hidden(li):
                    continue
                i += 1
                mark = f"{i}. " if t == "ol" else "- "
                body = "\n\n".join(self.blocks(li)) if has_block(li) else self.join(li.children).strip()
                if body:
                    items.append(mark + body.replace("\n", "\n" + " " * len(mark)))
            return ["\n".join(items)] if items else []
        if t == "table":
            head, rows = None, []
            for tr in n.iter():
                if tr.tag != "tr":
                    continue
                cells = [c for c in tr.children if isinstance(c, Node) and c.tag in ("th", "td")]
                vals = [self.join(c.children).strip() for c in cells]
                if head is None and (tr.parent.tag == "thead" or all(c.tag == "th" for c in cells)):
                    head = vals
                else:
                    rows.append(vals)
            cap = n.find("caption")
            if head is None and rows:  # no header row in the page: an empty one, so the first row stays a row
                head = [""] * max(len(r) for r in rows)
            return [((f"**{cap.text().strip()}**\n\n") if cap else "") + md_table(rows, head)]
        if t == "dl":
            items = []
            for d in n.iter():
                if d.tag == "dt":
                    dd = d.parent.find("dd") if d.parent.tag != "dl" else None
                    if dd is None:  # dt/dd as siblings
                        sib = d.parent.children
                        i = sib.index(d)
                        dd = next((s for s in sib[i + 1:] if isinstance(s, Node) and s.tag == "dd"), None)
                    items.append(f"- **{self.join(d.children).strip()}**: {self.join(dd.children).strip() if dd else ''}")
            return ["\n".join(items)] if items else []
        if t == "details":
            out = []
            for k in n.children:
                if isinstance(k, Node) and k.tag == "summary":
                    s = self.join(k.children).strip()
                    if s:
                        out.append(f"**{s}**")
            rest = Node("div")
            rest.children = [k for k in n.children if not (isinstance(k, Node) and k.tag == "summary")]
            return out + self.blocks(rest)
        if t == "blockquote":
            inner = "\n\n".join(self.blocks(n))
            return ["\n".join("> " + l if l else ">" for l in inner.splitlines())] if inner else []
        if t == "pre":
            return ["```\n" + n.text().strip("\n") + "\n```"]
        if t == "hr":
            return ["---"]
        if t == "div" and "key" in n.cls():  # answer key + each model's answer: one per line
            items = [self.join(k.children).strip() for k in n.children if isinstance(k, Node)]
            return ["\n".join(f"- {x}" for x in items if x)]
        if t == "footer":
            spans = [k for k in n.iter() if k.tag == "span" and k.parent is not None and "foot-row" in k.parent.cls()]
            return [self.join(k.children).strip() for k in spans] or self.blocks(n)
        if t == "a":  # a link wrapping a card: the card's text, then the link
            inner = self.blocks(n)
            h = self.href(n.attrs.get("href", ""))
            return inner + ([f"[More: {LABEL.get(Path(urllib.parse.urlparse(h).path).stem, h)}]({h})"] if h else [])
        return self.blocks(n)


def page_markdown(name, root):
    url = f"{BASE}/" if name == "index" else f"{BASE}/{name}.html"
    md = Markdown(url)
    main = root.find("main") or root.find("body")
    blocks = md.blocks(main)
    h1 = next((i for i, b in enumerate(blocks) if b.startswith("# ")), None)
    title = blocks.pop(h1) if h1 is not None else f"# {root.find('title').text().strip()}"
    foot = root.find("footer")
    tail = ["---", *md.block(foot)] if foot else []
    head = [title, f"Source: {url} · plain-text twin of that page, made from it at build time · all pages: {BASE}/llms.txt"]
    return "\n\n".join(head + blocks + tail).strip() + "\n"


def meta_description(root):
    m = next((n for n in root.iter() if n.tag == "meta" and n.attrs.get("name") == "description"), None)
    return m.attrs.get("content", "").strip() if m else ""


# ---- extra files ----------------------------------------------------------------------------------------------------------

def json_ld(desc):
    meta = json.loads((WEB / "data" / "meta.json").read_text())
    data = [("models.json", "Scores by model, with 95% intervals"), ("tasks.json", "Scores by task"),
            ("tools.json", "Scores with and without the planning engine as tools"), ("gauntlet.json", "Whole-household decisions, alone and with the engine"),
            ("v2.json", "Wrong facts and the newer, harder set")]
    return {
        "@context": "https://schema.org", "@type": "Dataset", "name": "PlannerBench",
        "description": desc, "url": f"{BASE}/",
        "keywords": ["AI benchmark", "retirement planning", "tax", "Social Security", "required minimum distributions", "Medicare IRMAA", "LLM evaluation"],
        "creator": {"@type": "Person", "name": "Peyton Thalman", "url": "https://peytonthalman.com"},
        "isAccessibleForFree": True,
        "measurementTechnique": f"{meta['questions']:,} public questions across {meta['tasks']} tasks with one exact answer each, graded by script against an answer key checked against IRS, SSA and CMS publications",
        "distribution": [{"@type": "DataDownload", "name": d, "encodingFormat": "application/json", "contentUrl": f"{BASE}/data/{f}"} for f, d in data if (WEB / "data" / f).exists()],
        "subjectOf": {"@type": "WebPage", "url": f"{BASE}/llms.txt", "name": "PlannerBench as plain text for AI readers"},
    }


NARROW = 420  # headless Chrome lays out no narrower than about 500px, which still gives the phone version of each chart
CHART_RE = re.compile(r'(<div class="chart"[^>]*\bid="([\w-]+)"[^>]*>)(<svg\b.*?</svg>)', re.S)


def add_narrow_charts(wide, narrow):
    """Each app.js chart twice: the desktop drawing (svg.chart-wide) and the phone one (svg.chart-narrow); CSS shows one."""
    small = {m[2]: m[3] for m in CHART_RE.finditer(narrow)}

    def both(m):
        alt = small.get(m[2])
        if not alt:
            return m[0]
        return m[1] + m[3].replace("<svg", '<svg class="chart-wide"', 1) + alt.replace("<svg", '<svg class="chart-narrow" aria-hidden="true"', 1)
    return CHART_RE.sub(both, wide)


def finish_html(name, src, desc):
    """Baked DOM → the HTML we ship: no app.js, plus canonical, Markdown alternate and (home) JSON-LD."""
    src = re.sub(r'\s*<script\b[^>]*\bsrc="app\.js[^"]*"[^>]*>\s*</script>', "", src)
    url = f"{BASE}/" if name == "index" else f"{BASE}/{name}.html"
    add = [f'<link rel="canonical" href="{url}">', f'<link rel="alternate" type="text/markdown" href="/{name}.md" title="This page as Markdown">']
    if name == "index":
        add.append('<link rel="alternate" type="text/plain" href="/llms.txt" title="llms.txt">')
        add.append('<script type="application/ld+json">' + json.dumps(json_ld(desc), ensure_ascii=False).replace("</", "<\\/") + "</script>")
    src = src.replace("</head>", "\n".join(add) + "\n</head>", 1)
    return "<!doctype html>\n" + src.strip() + "\n"


def demote(md):
    out, fence = [], False
    for l in md.splitlines():
        if l.startswith("```"):
            fence = not fence
        out.append("#" + l if (not fence and re.match(r"#{1,5} ", l)) else l)
    return "\n".join(out)


def llms_txt(pages):
    home = pages["index"]
    lines = ["# PlannerBench", "", f"> {home['desc']}", "",
             "A benchmark of AI models on 2026 U.S. retirement-planning math (federal tax, Social Security, required minimum "
             "distributions, Medicare IRMAA) with an exact answer key, built by Peyton Thalman (https://peytonthalman.com). "
             "Every number on the site comes from graded runs and can be rebuilt from the saved replies. Each link below is a "
             "Markdown twin of a page, made from the finished page at build time; nothing in it is hidden from the human version.",
             "", "## Pages", ""]
    for n in ORDER:
        if n in pages and n not in OPTIONAL:
            lines.append(f"- [{LABEL[n]}]({BASE}/{n}.md): {pages[n]['desc']}")
    lines += ["", "## Data", ""]
    for f, d in [("models.json", "scores by model with 95% intervals"), ("tasks.json", "scores by task"), ("mistakes.json", "wrong answers by kind"),
                 ("tools.json", "the same hard questions without and with the planning engine's tools"), ("gauntlet.json", "whole-household decisions, alone and with the engine"),
                 ("v2.json", "bad inputs and the hard tier")]:
        if (WEB / "data" / f).exists():
            lines.append(f"- [{f}]({BASE}/data/{f}): {d}")
    lines += ["", "## Optional", "", f"- [The whole site in one file]({BASE}/llms-full.txt): every page, table and chart's numbers as one Markdown document"]
    for n in ORDER:
        if n in pages and n in OPTIONAL:
            lines.append(f"- [{LABEL[n]}]({BASE}/{n}.md): {pages[n]['desc']}")
    return "\n".join(lines) + "\n"


def llms_full(pages):
    parts = ["# PlannerBench: the whole site as one document", "",
             f"> {pages['index']['desc']}", "",
             f"Every page of {BASE} in reading order, made from the finished pages at build time. Tables are kept as tables; each chart is "
             "followed by a table of the numbers it shows; text behind toggles is written out. The page map is at "
             f"{BASE}/llms.txt."]
    for n in ORDER:
        if n in pages and n != "agent":
            parts += ["", "---", "", demote(pages[n]["md"]).strip()]
    return "\n".join(parts) + "\n"


def vercel_json():
    redirects = []
    for old, new in REDIRECTS.items():
        for src in (f"/{old}.html", f"/{old}"):
            redirects.append({"source": src, "destination": f"/{new}.html", "permanent": True})
    redirects.append({"source": "/agent", "destination": "/agent.html", "permanent": False})
    md = [{"key": "Content-Type", "value": "text/markdown; charset=utf-8"}, {"key": "Content-Disposition", "value": "inline"}]
    txt = [{"key": "Content-Type", "value": "text/plain; charset=utf-8"}]
    return {"redirects": redirects,
            "headers": [{"source": "/(.*)\\.md", "headers": md}, {"source": "/llms.txt", "headers": txt}, {"source": "/llms-full.txt", "headers": txt}]}


def sitemap(names):
    today = date.today().isoformat()
    urls = "".join(f"  <url><loc>{BASE}/{'' if n == 'index' else n + '.html'}</loc><lastmod>{today}</lastmod></url>\n" for n in names)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'


# ---- main -------------------------------------------------------------------------------------------------------------

def main():
    if not Path(CHROME).exists():
        sys.exit(f"Chrome not found at {CHROME}; set CHROME=/path/to/chrome")
    names = sorted(p.stem for p in WEB.glob("*.html"))
    names.sort(key=lambda n: ORDER.index(n) if n in ORDER else len(ORDER))
    unknown = [n for n in names if n not in ORDER]
    if unknown:
        print(f"note: pages not in the reading order (added at the end): {', '.join(unknown)}")
        for n in unknown:
            LABEL.setdefault(n, n.replace("-", " ").capitalize())
    ids = fill_ids()
    httpd = serve()
    port = httpd.server_address[1]
    try:
        with tempfile.TemporaryDirectory(prefix="bake-") as tmp, concurrent.futures.ThreadPoolExecutor(max_workers=min(6, len(names))) as pool:
            jobs = {n: pool.submit(render, f"http://127.0.0.1:{port}/{n}.html", f"{tmp}/{n}") for n in names}
            dom = {n: j.result() for n, j in jobs.items()}
            # app.js draws some charts at the container's width and redrew them on resize. Baked, a desktop-width
            # chart would shrink to unreadable text on a phone, so pages with such charts are rendered narrow too.
            narrow = [n for n in names if CHART_RE.search(dom[n])]
            jobs = {n: pool.submit(render, f"http://127.0.0.1:{port}/{n}.html", f"{tmp}/{n}-narrow", NARROW) for n in narrow}
            for n, j in jobs.items():
                dom[n] = add_narrow_charts(dom[n], j.result())
    finally:
        httpd.shutdown()

    # Page names for llms.txt come from the home page's nav and footer, so they follow whatever the pages call themselves.
    for a in parse(dom["index"]).iter():
        if a.tag == "a" and a.parent is not None and a.parent.tag in ("nav", "span") and "mode" not in a.parent.cls():
            stem = Path(a.attrs.get("href", "")).stem
            if stem in LABEL and stem != "index" and a.text().strip() and not a.attrs.get("href", "").startswith("http"):
                LABEL[stem] = re.sub(r"\s+", " ", a.text()).strip()

    pages, problems = {}, []
    for n in names:
        root = parse(dom[n])
        desc = meta_description(root)
        out = finish_html(n, dom[n], desc)
        baked = parse(out)
        problems += check(n, baked, ids)
        pages[n] = {"html": out, "desc": desc, "md": page_markdown(n, baked)}
    if problems:
        print("BAKE FAILED: these slots were not filled (site/ left unchanged):\n  " + "\n  ".join(problems))
        sys.exit(1)

    # Build next to site/, then swap the contents in, keeping site/'s dotfiles (.vercel, .env.local, ignore files).
    stage = ROOT / ".bake-stage"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir()
    for p in WEB.iterdir():
        if p.suffix == ".html" or p.name in SKIP_COPY or p.name.startswith("."):
            continue
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, stage / p.name)
    for n, pg in pages.items():
        (stage / f"{n}.html").write_text(pg["html"])
        (stage / f"{n}.md").write_text(pg["md"])
    (stage / "llms.txt").write_text(llms_txt(pages))
    (stage / "llms-full.txt").write_text(llms_full(pages))
    (stage / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    (stage / "sitemap.xml").write_text(sitemap(names))
    (stage / "vercel.json").write_text(json.dumps(vercel_json(), indent=2) + "\n")

    SITE.mkdir(exist_ok=True)
    for p in SITE.iterdir():
        if not p.name.startswith("."):
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    for p in stage.iterdir():
        shutil.move(str(p), SITE / p.name)
    stage.rmdir()
    print(f"Baked {len(pages)} pages into site/ ({', '.join(names)}), with .md twins, llms.txt, llms-full.txt, sitemap.xml, robots.txt, vercel.json")


if __name__ == "__main__":
    main()
