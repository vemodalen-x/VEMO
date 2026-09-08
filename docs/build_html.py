#!/usr/bin/env python3
"""Render VEMO's human-facing Markdown into a themed, navigable HTML site under docs/html/.

Pre-generated output is committed so the docs are readable with no build step or dependency. To
regenerate after editing the Markdown:  python3 docs/build_html.py   (needs `pip install markdown`).
The generated pages cross-link (a .md link becomes the corresponding .html) and share one theme.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "html")

# (group, [repo-relative markdown sources]) — order defines the sidebar.
GROUPS = [
    ("Get started", ["README.md", "docs/INSTALL.md", "docs/USAGE.md", "docs/QUICKSTART.md", "docs/MENTAL_MODEL.md"]),
    ("Design", ["docs/DESIGN_LITE.md", "docs/PLATFORM.md", "docs/EXTENSIONS.md", "docs/ADAPTERS.md"]),
    ("Understand", ["docs/SCALING.md", "docs/COMPLIANCE.md", "docs/OWASP_AGENTIC_TOP10.md", "AGENTS.md"]),
    ("Reference", ["docs/INDEX.md", "CHANGELOG.md", "ROADMAP.md", "SECURITY.md", "CONTRIBUTING.md", "CONTRIBUTORS.md"]),
    ("Announcement", ["docs/ANNOUNCEMENT.md"]),
    ("Specs", ["specs/safety.spec.md", "specs/task.spec.md", "specs/verify.spec.md", "specs/capability.spec.md",
               "specs/concurrency.spec.md", "specs/coding.spec.md", "specs/comment.spec.md", "specs/automation.spec.md"]),
]

CSS = """
:root{--teal:#0d9488;--teal-d:#0f766e;--accent:#14b8a6;--bg:#f8fafc;--panel:#fff;--ink:#1e293b;
--muted:#64748b;--line:#e2e8f0;--code:#f1f5f9;--codeink:#0f172a}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg)}
a{color:var(--teal-d);text-decoration:none}a:hover{text-decoration:underline}
.layout{display:flex;min-height:100vh;max-width:1200px;margin:0 auto}
nav.side{width:262px;flex:0 0 262px;background:var(--panel);border-right:1px solid var(--line);
padding:22px 16px;position:sticky;top:0;height:100vh;overflow:auto}
nav.side .brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:20px;color:var(--teal-d);
margin:0 6px 4px;letter-spacing:.3px}
nav.side .brand img{width:30px;height:30px}
nav.side .tag{color:var(--muted);font-size:11.5px;margin:0 6px 16px;line-height:1.45}
nav.side .grp{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
margin:18px 6px 6px;font-weight:700}
nav.side a.item{display:block;padding:5px 10px;border-radius:7px;color:var(--ink);font-size:14px}
nav.side a.item:hover{background:var(--code);text-decoration:none}
nav.side a.item.active{background:var(--teal);color:#fff;font-weight:600}
nav.side a.guide{display:block;margin:4px 6px 8px;padding:8px 10px;border-radius:8px;background:linear-gradient(135deg,var(--teal),var(--accent));color:#fff;font-weight:600;font-size:13.5px}
main{flex:1;min-width:0;padding:42px 52px 80px}
.content{max-width:820px}
h1,h2,h3,h4{line-height:1.25;font-weight:700;margin:1.6em 0 .5em}
h1{font-size:2em;margin-top:.2em;padding-bottom:.3em;border-bottom:2px solid var(--line)}
h2{font-size:1.45em;padding-bottom:.25em;border-bottom:1px solid var(--line)}
h3{font-size:1.18em}
p,li{color:#27313f}
code{background:var(--code);color:var(--codeink);padding:.15em .4em;border-radius:5px;font-size:.88em;
font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
pre{background:#0f172a;color:#e2e8f0;padding:16px 18px;border-radius:10px;overflow:auto;font-size:13.5px;line-height:1.55}
pre code{background:none;color:inherit;padding:0}
blockquote{margin:1em 0;padding:.4em 1.1em;border-left:4px solid var(--accent);background:#f0fdfa;
color:#334155;border-radius:0 8px 8px 0}
table{border-collapse:collapse;width:100%;margin:1.2em 0;font-size:14.5px;display:block;overflow:auto}
th,td{border:1px solid var(--line);padding:8px 12px;text-align:left;vertical-align:top}
th{background:var(--code);font-weight:700}
tr:nth-child(even) td{background:#fcfdfe}
hr{border:none;border-top:1px solid var(--line);margin:2em 0}
img{max-width:100%}
.topbar{display:none}
.footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}
@media(max-width:860px){.layout{display:block}nav.side{width:auto;height:auto;position:static;border-right:none;border-bottom:1px solid var(--line)}main{padding:24px 20px 60px}}
"""


def title_of(src, body_md):
    m = re.search(r"^#\s+(.+)$", body_md, re.M)
    return (m.group(1).strip() if m else os.path.basename(src)).replace("`", "")


RENAME = {"INDEX.md": "guide-index.html"}  # avoid a case-insensitive-FS clash with the generated index.html


def out_name(src):
    b = os.path.basename(src)
    if b in RENAME:
        return RENAME[b]
    return b[:-3] + ".html" if b.endswith(".md") else b


def rewrite_links(html):
    """Make in-doc links work from docs/html/: .md -> .html, assets -> ../../assets, GUIDE -> ../GUIDE, root files -> ../../."""
    def repl(m):
        attr, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://", "#", "mailto:", "data:")):
            return m.group(0)
        path, frag = (url.split("#", 1) + [""])[:2]
        frag = ("#" + frag) if "#" in url else ""
        base = os.path.basename(path)
        low = base.lower()
        if low.endswith(".md"):
            new = (RENAME[base] if base in RENAME else base[:-3] + ".html") + frag
        elif low.endswith((".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp")):
            new = "../../assets/" + base
        elif low.endswith(".html"):
            new = ("../" + base + frag) if base.lower() == "guide.html" else (base + frag)
        else:
            new = "../../" + base + frag  # root files: LICENSE, vemo.config.yaml, …
        return f'{attr}="{new}"'
    return re.sub(r'(href|src)="([^"]+)"', repl, html)


def sidebar(active):
    rows = ['<a class="guide" href="../GUIDE.html">🖼️ Visual guide &amp; diagrams</a>',
            f'<a class="item{" active" if active=="index.html" else ""}" href="index.html">Home</a>']
    for grp, srcs in GROUPS:
        rows.append(f'<div class="grp">{grp}</div>')
        for src in srcs:
            on = out_name(src)
            rows.append(f'<a class="item{" active" if on==active else ""}" href="{on}">{TITLES.get(on, on)}</a>')
    return "\n".join(rows)


def page(active, title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · VEMO</title><style>{CSS}</style></head><body>
<div class="layout">
<nav class="side">
<div class="brand"><img src="../../assets/logo.svg" alt="">VEMO</div>
<div class="tag">Velocity-first · Enforced · Model-aware Orchestration</div>
{sidebar(active)}
</nav>
<main><div class="content">{body}
<div class="footer">VEMO documentation · rendered from Markdown by <code>docs/build_html.py</code>.
For the rich visual guide see <a href="../GUIDE.html">GUIDE.html</a>.</div>
</div></main>
</div></body></html>"""


def main():
    try:
        import markdown
    except ImportError:
        sys.exit("needs the 'markdown' package: pip install markdown")
    os.makedirs(OUT, exist_ok=True)
    md = markdown.Markdown(extensions=["extra", "sane_lists", "toc", "admonition"], output_format="html5")

    global TITLES
    TITLES = {}
    pages = []
    for _, srcs in GROUPS:
        for src in srcs:
            p = os.path.join(ROOT, src)
            if not os.path.exists(p):
                print(f"  skip (missing): {src}"); continue
            text = open(p, encoding="utf-8").read()
            on = out_name(src)
            TITLES[on] = title_of(src, text)
            pages.append((src, on, text))

    n = 0
    for src, on, text in pages:
        md.reset()
        body = rewrite_links(md.convert(text))
        open(os.path.join(OUT, on), "w", encoding="utf-8").write(page(on, TITLES[on], body))
        n += 1

    # landing page
    cards = []
    for grp, srcs in GROUPS:
        items = "".join(f'<li><a href="{out_name(s)}">{TITLES.get(out_name(s), s)}</a></li>'
                        for s in srcs if out_name(s) in TITLES)
        cards.append(f"<h2>{grp}</h2><ul>{items}</ul>")
    intro = ('<h1>VEMO documentation</h1><p>Governance for AI coding agents that <em>accelerates</em> '
             'developers — mechanism over prose, and it <em>proves</em> its gates fire. '
             'For the rich visual guide (architecture, lifecycle, ceremony matrix) see '
             '<a href="../GUIDE.html">GUIDE.html</a>.</p>')
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page("index.html", "Docs", intro + "".join(cards)))
    print(f"  rendered {n} pages + index -> docs/html/")

    # Ship the three essential guides with the runtime UI, with no Markdown dependency at runtime.
    help_dir = os.path.join(ROOT, "ui", "help")
    os.makedirs(help_dir, exist_ok=True)
    help_names = {"INSTALL.md": "install.html", "USAGE.md": "usage.html", "DESIGN_LITE.md": "design.html"}
    def help_link(match):
        attr, url = match.group(1), match.group(2)
        if url.startswith(("http:", "https:", "#")):
            return match.group(0)
        name = os.path.basename(url)
        target = "/help/" + help_names[name] if name in help_names else "https://github.com/vemodalen-x/VEMO/blob/main/docs/" + name
        return f'{attr}="{target}"'
    for name, output in help_names.items():
        md.reset()
        with open(os.path.join(ROOT, "docs", name), encoding="utf-8") as stream:
            body = re.sub(r'(href|src)="([^"]+)"', help_link, md.convert(stream.read()))
        document = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>VEMO 使用帮助</title><link rel="stylesheet" href="/style.css"></head>'
                    '<body><article class="help-content"><a href="/">← 返回安装向导</a>' + body + '</article></body></html>')
        with open(os.path.join(help_dir, output), "w", encoding="utf-8") as stream:
            stream.write(document)
    print("  rendered 3 offline UI help pages -> ui/help/")


if __name__ == "__main__":
    main()
