# Entry point. `python scripts/build.py` fetches the public data, draws every SVG into assets/ and writes
# README.md. `--offline` uses scripts/fixtures/ only (no network, state.json untouched).
# `--record-fixtures` does a live run that also saves the raw responses into scripts/fixtures/.
# Nothing is written unless every card could be drawn: a failed source falls back to its copy in
# scripts/state.json, and an unreadable contribution calendar stops the build and keeps yesterday's cards.
import argparse, json, os, sys
from datetime import date, datetime, timezone

import board, cards, fetch, graphs, phone, readme
from svgkit import HERE as SCRIPTS

ROOT = os.path.dirname(SCRIPTS)
THEMES = cards.THEMES
KB_LIMIT = 150


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf8") as f:
        return json.load(f)


def make_assets(data, P):
    """name -> Svg for every image the README uses."""
    out = {}
    for t in THEMES:
        out[f"hero-{t}.svg"] = cards.hero(t, data, P)
        out[f"hero-phone-{t}.svg"] = phone.hero_phone(t, data, P)
        out[f"github-{t}.svg"] = board.github_board(t, data)
        out[f"github-phone-{t}.svg"] = phone.github_board_phone(t, data)
        out.update(graphs.make_graphs(t, data, date.fromisoformat(data["today"]))[0])
        out[f"whoami-{t}.svg"] = cards.whoami(t, data, P)
        out[f"whoami-phone-{t}.svg"] = phone.whoami_phone(t, data, P)
        out[f"label-ship-{t}.svg"] = cards.label(t, "What I ship", f"{len(P['apps'])} flagship apps", "rd", "card")
        out[f"label-ship-phone-{t}.svg"] = phone.label_phone(t, "What I ship", "rd")
        if "youtube" in P["links"]:
            out[f"label-videos-{t}.svg"] = cards.label(t, "Latest videos", f"YouTube {P['links']['youtube']['handle']}", "yt", "card")
            out[f"label-videos-phone-{t}.svg"] = phone.label_phone(t, "Latest videos", "yt")
        for key, name, fill, icon in (("youtube", "yt", "yt", "play"), ("x", "x", "x", None), ("linkedin", "li", "lx", None), ("site", "site", "card", None)):
            if key not in P["links"]:
                continue
            L = P["links"][key]
            out[f"badge-{name}-{t}.svg"] = cards.badge(t, L["label"], L["handle"], fill, icon)
        for a in P["apps"]:
            out[f"app-{a['id']}-{t}.svg"] = cards.app(t, a, data, P)
            out[f"app-{a['id']}-phone-{t}.svg"] = phone.app_phone(t, a, data, P)
        for v in data.get("videos", {}).get("videos", []):
            out[f"video-{v['id']}-{t}.svg"] = cards.video(t, v)
            out[f"video-{v['id']}-phone-{t}.svg"] = phone.video_phone(t, v)
    return out


def numbers(data, P):
    """(label, value, source) for every number the build uses, printed on every run."""
    c, r = data["contrib"], data["repos"]
    gh = f"github.com/users/{P['user']}/contributions"
    cur, best = c["current_streak"], c["longest_streak"]
    v = cards.challenge_view(data.get("challenge"))
    ch = f"{v['title']}: {v['count']}, {v['note']}" if v else "no challenge source on this profile, nothing shown"
    streak = f"{cur['days']} days since {cur['start']}" if cur["days"] > 0 and cur["start"] else "no streak right now"
    return [
        ("contributions in the last year", fmt_(c["last_year"]), gh),
        ("contributions this calendar year", fmt_(c["this_year"]), gh + "?from=&to= (year page)"),
        ("contributions since %s" % c["since_year"], fmt_(c["all_time"]), gh + " (every year page)"),
        ("current streak", streak, gh),
        ("longest streak", f"{best['days']} days, {best['start']} to {best['end']}", gh),
        ("public repos (non-fork)", str(r["public_repos"]), f"api.github.com/users/{P['user']}/repos"),
        ("stars earned", str(r["stars"]), f"api.github.com/users/{P['user']}/repos"),
        ("release downloads", fmt_(r["downloads"]), "api.github.com repos/*/releases"),
        ("challenge", ch, "profile.json"),
    ]


def fmt_(n):
    return f"{n:,}"


def run(offline=False, record=False, out_root=ROOT, state_path=None, today=None, net=None, log=print):
    """Builds everything in memory first, then writes it. Returns {"data", "files", "warnings"}."""
    P = load_json(os.path.join(ROOT, "profile.json"))
    state_path = state_path or os.path.join(SCRIPTS, "state.json")
    state = None if offline else load_json(state_path)
    net = net or fetch.Net(offline=offline, record=record)
    if today is None:
        if offline:
            today = date.fromisoformat(load_json(os.path.join(fetch.FIXTURES, "meta.json"))["today"])
        else:
            today = datetime.now(timezone.utc).date()
    data, new_state, notes = fetch.collect(net, P, today, state)
    svgs = make_assets(data, P)
    files, warnings = {}, []
    for name, s in svgs.items():
        files[f"assets/{name}"] = s.render()
        if s.overflow:
            warnings.append(f"{name}: text runs past the edge: {s.overflow}")
        if len(files[f"assets/{name}"]) > KB_LIMIT * 1024:
            warnings.append(f"{name}: {len(files[f'assets/{name}']) // 1024} KB is over {KB_LIMIT} KB")
    files["README.md"] = readme.render(data, P)
    # only now touch the disk
    assets_dir = os.path.join(out_root, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    for old in os.listdir(assets_dir):
        if old.endswith(".svg") and f"assets/{old}" not in files:
            os.remove(os.path.join(assets_dir, old))
    for rel, text in files.items():
        with open(os.path.join(out_root, rel), "w", encoding="utf8", newline="\n") as f:
            f.write(text if rel != "README.md" else text.rstrip("\n") + "\n")
    if not offline:
        with open(state_path, "w", encoding="utf8", newline="\n") as f:
            json.dump(new_state, f, indent=1, ensure_ascii=False)
            f.write("\n")
    if record:
        with open(os.path.join(fetch.FIXTURES, "meta.json"), "w", encoding="utf8") as f:
            json.dump({"today": today.isoformat(), "note": "the day the fixtures were recorded; offline builds use it as today"}, f)
    log(f"built {len(svgs)} SVGs for {today.isoformat()} ({'offline fixtures' if offline else 'live'})")
    for what, where in notes:
        log(f"  source {what}: {where}")
    for label, value, src in numbers(data, P):
        log(f"  {label}: {value}   [{src}]")
    for w in warnings:
        log(f"  WARNING {w}")
    # the cards above are drawn from saved data for a source that keeps failing; the caller turns the run red
    stale = fetch.stale_sources(new_state["good"], today)
    return {"data": data, "files": files, "warnings": warnings, "stale": stale}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="use scripts/fixtures/ only, no network")
    ap.add_argument("--record-fixtures", action="store_true", help="live run that also saves raw responses to scripts/fixtures/")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = run(offline=args.offline, record=args.record_fixtures)
    except fetch.SourceError as e:
        print(f"build stopped, nothing was written: {e}", file=sys.stderr)
        return 1
    if result["stale"]:
        what = ", ".join(f"{k} (last good fetch {d})" for k, d in result["stale"])
        print(f"::error::source not fetched for more than {fetch.STALE_AFTER_DAYS} days: {what}. "
              f"The cards were drawn from the saved copy; fix the source.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
