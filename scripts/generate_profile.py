#!/usr/bin/env python3
"""Generate the SVG assets for thakoreh's GitHub profile README.

Modeled on the all-SVG profile system used by github.com/ZazaGdev:
custom hero banner, social badges, a stats panel and contribution
graphs, each in light/dark and desktop/phone variants. All numbers
come from live GitHub data at generation time: the public
contributions calendar fragment, the users API, and the repos API.

Run: python3 scripts/generate_profile.py [output_dir]
Default output dir: ../assets relative to this script.
"""
import json
import math
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USER = "thakoreh"
UA = {"User-Agent": "profile-generator (github.com/thakoreh)"}

ICONS = {
    "x": "M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z",
    "linkedin": "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z",
    "github": "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12",
}

THEMES = {
    "light": dict(bg="#ffffff", panel="#f6f8fa", border="#d1d9e0", text="#1f2328",
                  muted="#59636e", accent="#1a7f37", chart="#26a641",
                  chart_fill="rgba(38,166,65,0.16)", grid="#e3e8ee"),
    "dark": dict(bg="#0d1117", panel="#161b22", border="#30363d", text="#e6edf3",
                 muted="#9198a1", accent="#3fb950", chart="#3fb950",
                 chart_fill="rgba(63,185,80,0.20)", grid="#21262d"),
}
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def get_stats():
    cal = fetch(f"https://github.com/users/{USER}/contributions")
    id2date = {}
    for tag in re.findall(r'<td[^>]*class="ContributionCalendar-day"[^>]*>', cal):
        i = re.search(r'id="(contribution-day-component-[\d-]+)"', tag)
        d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
        if i and d:
            id2date[i.group(1)] = d.group(1)
    by = {}
    for cid, txt in re.findall(r'for="(contribution-day-component-[\d-]+)"[^>]*>([^<]+)</tool-tip>', cal):
        d = id2date.get(cid)
        if not d:
            continue
        if txt.startswith("No contributions"):
            by[d] = 0
        else:
            m = re.search(r"([\d,]+) contribution", txt)
            by[d] = int(m.group(1).replace(",", "")) if m else 0
    user = json.loads(fetch(f"https://api.github.com/users/{USER}"))
    stars = 0
    page = 1
    while True:
        repos = json.loads(fetch(
            f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}"))
        if not isinstance(repos, list) or not repos:
            break
        stars += sum(r.get("stargazers_count", 0) for r in repos)
        if len(repos) < 100:
            break
        page += 1
    # All-time yearly totals from the community contributions API
    # (its per-year totals agree with the official calendar; its
    # daily distribution does not, so only totals are used).
    years = {}
    try:
        data = json.loads(fetch(f"https://github-contributions.vercel.app/api/v1/{USER}"))
        for y in data.get("years", []):
            years[int(y["year"])] = y["total"]
    except Exception:
        pass
    today = date.today()
    days = sorted(by)
    def window(n):
        s = today - timedelta(days=n - 1)
        return {k: v for k, v in by.items() if k >= str(s)}
    w365, w183 = window(365), window(183)
    best = cur = 0
    prev = None
    for d in days:
        dt = date.fromisoformat(d)
        if by[d] > 0:
            cur = cur + 1 if prev and (dt - prev).days == 1 else 1
            best = max(best, cur)
        else:
            cur = 0
        prev = dt
    cs = 0
    t = today
    if by.get(str(t), 0) == 0:
        t -= timedelta(days=1)
    while by.get(str(t), 0) > 0:
        cs += 1
        t -= timedelta(days=1)
    return dict(
        by=by, years=years, followers=user.get("followers", 0),
        repos=user.get("public_repos", 0), stars=stars,
        since=int((user.get("created_at") or "2018")[:4]),
        last_year=sum(w365.values()), last_6m=sum(w183.values()),
        all_time=sum(years.values()) if years else sum(by.values()),
        longest_streak=best, current_streak=cs,
        w365=w365, w183=w183,
    )


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_open(w, h, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f'<title>{esc(label)}</title>')


def panel(t, w, h, r=16):
    return (f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="{r}" '
            f'fill="{t["panel"]}" stroke="{t["border"]}"/>')


def text(x, y, s, size, fill, weight=400, anchor="start", spacing=None):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>{esc(s)}</text>')


def hero(t, phone=False):
    if phone:
        w, h = 420, 300
        label = "Hi, I'm Hiren Thakore. Senior software engineer building AI agent tooling and shipping indie apps, in public."
        parts = [svg_open(w, h, label), panel(t, w, h),
                 text(28, 52, "HI, I'M HIREN THAKORE", 13, t["accent"], 700, spacing="2"),
                 text(28, 98, "I build tooling for", 27, t["text"], 700),
                 text(28, 132, "AI-agent builders, and", 27, t["text"], 700),
                 text(28, 166, "ship indie apps with it.", 27, t["text"], 700),
                 text(28, 208, "Senior Dev 1 at Evertz · Toronto", 15, t["muted"]),
                 text(28, 234, "Building in public since 2018", 15, t["muted"]),
                 "</svg>"]
        return "".join(parts)
    w, h = 880, 216
    label = "Hi, I'm Hiren Thakore. Senior software engineer building AI agent tooling and shipping indie apps, in public."
    return "".join([
        svg_open(w, h, label), panel(t, w, h),
        text(48, 58, "HI, I'M HIREN THAKORE", 14, t["accent"], 700, spacing="2.5"),
        text(48, 110, "I build tooling for AI-agent builders,", 37, t["text"], 700),
        text(48, 156, "and ship indie apps with it.", 37, t["text"], 700),
        text(48, 192, "Senior Dev 1 at Evertz · Toronto · building in public since 2018", 16, t["muted"]),
        "</svg>"])


def icon_path(name, x, y, size, fill):
    scale = size / 24
    return (f'<g transform="translate({x},{y}) scale({scale:.3f})">'
            f'<path d="{ICONS[name]}" fill="{fill}"/></g>')


def globe_icon(x, y, size, color):
    r = size / 2
    cx, cy = x + r, y + r
    return (f'<g stroke="{color}" stroke-width="1.7" fill="none">'
            f'<circle cx="{cx}" cy="{cy}" r="{r - 1}"/>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{(r - 1) * 0.45:.1f}" ry="{r - 1}"/>'
            f'<line x1="{x + 1}" y1="{cy}" x2="{x + size - 1}" y2="{cy}"/></g>')


def badge(t, kind, label_text):
    h = 44
    icons = {"site": None, "x": "x", "linkedin": "linkedin", "github": "github"}
    text_w = math.ceil(len(label_text) * 7.4)
    w = 18 + 20 + 10 + text_w + 16
    parts = [svg_open(w, h, label_text),
             f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="{t["panel"]}" stroke="{t["border"]}"/>']
    if kind == "site":
        parts.append(globe_icon(16, 12, 20, t["text"]))
    else:
        parts.append(icon_path(icons[kind], 16, 12, 20, t["text"]))
    parts.append(text(48, 28, label_text, 14.5, t["text"], 600))
    parts.append("</svg>")
    return "".join(parts), w


def stats_panel(t, s, phone=False):
    items = [
        (f"{s['last_year']:,}", "contributions in the last year"),
        (f"{s['longest_streak']} days", "longest streak"),
        (f"{s['all_time']:,}", f"contributions since {s['since']}"),
        (f"{s['repos']}", "public repos"),
        (f"{s['followers']}", "followers"),
        (f"{s['stars']}", "stars earned"),
    ]
    label = "On GitHub: " + ", ".join(f"{v} {l}" for v, l in items) + "."
    if phone:
        w, h = 420, 300
        parts = [svg_open(w, h, label), panel(t, w, h),
                 text(28, 44, "ON GITHUB", 12, t["accent"], 700, spacing="2")]
        for i, (v, l) in enumerate(items):
            col, row = i % 2, i // 2
            x, y = 28 + col * 190, 96 + row * 76
            parts.append(text(x, y, v, 25, t["text"], 700))
            parts.append(text(x, y + 22, l, 12.5, t["muted"]))
        parts.append("</svg>")
        return "".join(parts)
    w, h = 880, 148
    parts = [svg_open(w, h, label), panel(t, w, h),
             text(48, 46, "ON GITHUB", 12, t["accent"], 700, spacing="2")]
    colw = (w - 96) / 3
    for i, (v, l) in enumerate(items):
        col, row = i % 3, i // 3
        x, y = 48 + col * colw, 84 + row * 52
        parts.append(text(x, y, v, 23, t["text"], 700))
        parts.append(text(x + 8 + len(v) * 13.2, y, l, 13.5, t["muted"]))
    parts.append("</svg>")
    return "".join(parts)


def graph(t, window, total, caption, phone=False):
    w = 420 if phone else 880
    h = 250 if phone else 264
    pad_l, pad_r, pad_top, pad_bot = (28, 28, 86, 30) if phone else (48, 48, 92, 34)
    days = sorted(window)
    vals = [window[d] for d in days]
    peak = max(vals) if vals else 0
    peak = max(peak, 1)
    gw, gh = w - pad_l - pad_r, h - pad_top - pad_bot
    step = gw / max(len(vals) - 1, 1)
    pts = []
    for i, v in enumerate(vals):
        x = pad_l + i * step
        y = pad_top + gh - (v / peak) * gh
        pts.append((x, y))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad_l},{pad_top + gh} " + line + f" {pad_l + gw},{pad_top + gh}"
    first = date.fromisoformat(days[0]).strftime("%b %Y") if days else ""
    last = date.fromisoformat(days[-1]).strftime("%b %Y") if days else ""
    label = f"{total:,} contributions in the {caption}"
    parts = [svg_open(w, h, label), panel(t, w, h),
             text(pad_l, 48, f"{total:,}", 30, t["text"], 700),
             text(pad_l + len(f"{total:,}") * 17.5 + 10, 48,
                  f"contributions in the {caption}", 15, t["muted"]),
             f'<line x1="{pad_l}" y1="{pad_top + gh}" x2="{pad_l + gw}" y2="{pad_top + gh}" stroke="{t["grid"]}" stroke-width="1"/>',
             f'<polygon points="{area}" fill="{t["chart_fill"]}"/>',
             f'<polyline points="{line}" fill="none" stroke="{t["chart"]}" stroke-width="2" stroke-linejoin="round"/>',
             text(pad_l, h - 10, first, 11.5, t["muted"]),
             text(pad_l + gw, h - 10, last, 11.5, t["muted"], anchor="end"),
             "</svg>"]
    return "".join(parts)


def years_chart(t, s):
    years = s["years"]
    if not years:
        return None
    ys = sorted(years)
    w, h = 880, 64 + len(ys) * 34
    peak = max(years.values()) or 1
    label = "Contributions by year: " + ", ".join(f"{y}: {years[y]:,}" for y in ys)
    parts = [svg_open(w, h, label), panel(t, w, h),
             text(48, 42, "YEAR BY YEAR", 12, t["accent"], 700, spacing="2")]
    for i, y in enumerate(ys):
        yy = 78 + i * 34
        bw = (years[y] / peak) * 560
        parts.append(text(48, yy, str(y), 14, t["muted"], 600))
        parts.append(f'<rect x="100" y="{yy - 13}" width="{bw:.0f}" height="16" rx="4" fill="{t["chart"]}"/>')
        parts.append(text(108 + bw, yy, f"{years[y]:,}", 13.5, t["text"], 600))
    parts.append("</svg>")
    return "".join(parts)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "assets"
    out.mkdir(parents=True, exist_ok=True)
    s = get_stats()
    print({k: s[k] for k in ("last_year", "last_6m", "all_time", "longest_streak",
                             "current_streak", "followers", "repos", "stars")})
    files = {}
    for name, t in THEMES.items():
        files[f"hero-{name}.svg"] = hero(t)
        files[f"hero-phone-{name}.svg"] = hero(t, phone=True)
        files[f"github-{name}.svg"] = stats_panel(t, s)
        files[f"github-phone-{name}.svg"] = stats_panel(t, s, phone=True)
        files[f"graph-6m-{name}.svg"] = graph(t, s["w183"], s["last_6m"], "last 6 months")
        files[f"graph-6m-phone-{name}.svg"] = graph(t, s["w183"], s["last_6m"], "last 6 months", phone=True)
        files[f"graph-12m-{name}.svg"] = graph(t, s["w365"], s["last_year"], "last 12 months")
        yc = years_chart(t, s)
        if yc:
            files[f"years-{name}.svg"] = yc
        for kind, txt in [("site", "hirenthakore.com"), ("x", "X @hirenthakore"),
                          ("linkedin", "LinkedIn"), ("github", "GitHub @thakoreh")]:
            svg, _ = badge(t, kind, txt)
            files[f"badge-{kind}-{name}.svg"] = svg
    for fn, content in files.items():
        (out / fn).write_text(content, encoding="utf-8")
    print(f"wrote {len(files)} files to {out}")


if __name__ == "__main__":
    main()
