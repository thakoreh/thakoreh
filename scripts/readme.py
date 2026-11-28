# README.md from a template, so the numbers in every image's alt text stay current.
# Every image is a <picture> with a dark <source>. Pictures in PHONE also get phone sources.
# Source order matters: the browser takes the first one whose media matches, so dark+phone comes
# first, then phone, then dark, then the light desktop <img>.
from datetime import date
from html import escape

from board import board_label
from cards import app_fact, app_label, fmt, hero_label, whoami_label
from graphs import graph_titles, last_days, title_of, total_of


PHONE = ("hero", "github", "whoami")      # every picture that has a phone variant is called with phone=True


def line_title(data, today):
    return title_of(total_of(last_days(data, today)), "in the last 30 days")


def picture(name, width, alt, phone=False):
    a = f"assets/{name}"
    srcs = []
    if phone:
        srcs.append(f'<source media="(prefers-color-scheme: dark) and (max-width: 600px)" srcset="{a}-phone-dark.svg">')
        srcs.append(f'<source media="(max-width: 600px)" srcset="{a}-phone-light.svg">')
    srcs.append(f'<source media="(prefers-color-scheme: dark)" srcset="{a}-dark.svg">')
    attr = f'height="{width[1:]}"' if width.startswith("h") else f'width="{width}"'
    return f'<picture>{"".join(srcs)}<img src="{a}-light.svg" {attr} alt="{escape(alt, quote=True)}"></picture>'


def link(url, inner):
    return f'<a href="{url}">{inner}</a>'


def render(data, P):
    L = P["links"]
    out = [link(L["site"]["url"], picture("hero", "100%", hero_label(P, data), "hero" in PHONE)), ""]
    badges = []
    for key, name in (("youtube", "yt"), ("x", "x"), ("linkedin", "li"), ("site", "site")):
        if key not in L:
            continue
        alt = f"{L[key]['label']} {L[key]['handle']}".strip()
        badges.append(link(L[key]["url"], picture(f"badge-{name}", "h44", alt)))
    out += ['<p align="center">', *badges, "</p>", ""]
    out += [picture("github", "100%", board_label(data), "github" in PHONE), ""]
    for key, summary, total, title in graph_titles(data, date.fromisoformat(data["today"])):
        pic = picture(f"graph-{key}", "100%", title, True)
        if summary is None:
            out += [pic, ""]
        else:
            unit = "contribution" if total == 1 else "contributions"
            out += [f"<details><summary>{summary}: {fmt(total)} {unit}</summary>", "", pic, "", "</details>", ""]
    out += [picture("line-30d", "100%", line_title(data, date.fromisoformat(data["today"])), True), ""]
    out += [picture("whoami", "100%", whoami_label(data, P), "whoami" in PHONE), ""]
    out += [picture("label-ship", "100%", "What I ship", True), ""]
    apps = []
    for a in P["apps"]:
        alt = app_label(a, app_fact(a, data, P))
        apps.append(link(a["url"], picture(f"app-{a['id']}", "49%", alt, True)))
    out += ['<p align="center">', *apps, "</p>", ""]
    S = P["store_links"]
    more = " · ".join(link(m["url"], m["name"]) for m in P["more"])
    out += [f'<p align="center"><sub>Reelish on {link(S["reelish_google_play"], "Google Play")} · more ships: {more}</sub></p>', ""]
    if data.get("videos", {}).get("videos"):
        out += [picture("label-videos", "100%", "Latest videos", True), ""]
        vids = [link(f"https://www.youtube.com/watch?v={v['id']}", picture(f"video-{v['id']}", "32%", v["title"], True))
                for v in data["videos"]["videos"]]
        out += ['<p align="center">', *vids, "</p>", ""]
    out += [f'<p align="center"><sub>Drawn in the ZazaG Dev design system · numbers redrawn every night by a GitHub Action · '
            f'{link(L["site"]["url"], "hirenthakore.com")}</sub></p>', ""]
    return "\n".join(out)
