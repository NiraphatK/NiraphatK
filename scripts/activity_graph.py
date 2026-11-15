#!/usr/bin/env python3
"""Render the last 31 days of GitHub contributions as an SVG line chart.

Replaces the hosted github-readme-activity-graph widget, whose public
instance stopped serving (HTTP 402).

Usage: GITHUB_TOKEN=... python3 scripts/activity_graph.py OUTPUT.svg
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request

LOGIN = "NiraphatK"
DAYS = 31

# tokyonight, matching the previous widget (bg_color=0f141c)
BG, TITLE, LINE, POINT, GRID, TEXT = "#0f141c", "#70a5fd", "#38bdae", "#bf91f3", "#2a3245", "#a9b1d6"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

W, H = 1000, 360
LEFT, RIGHT, TOP, BOTTOM = 80, 960, 70, 290


def fetch_days() -> list[tuple[dt.date, int]]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN (or GH_TOKEN) is required")
    query = """query($login: String!) { user(login: $login) { contributionsCollection {
                 contributionCalendar { weeks { contributionDays { date contributionCount } } } } } }"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": f"{LOGIN}-activity-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [
        (dt.date.fromisoformat(d["date"]), d["contributionCount"])
        for week in weeks
        for d in week["contributionDays"]
    ]
    return sorted(days)[-DAYS:]


def render(days: list[tuple[dt.date, int]]) -> str:
    peak = max(c for _, c in days)
    y_max = max(4, -(-peak // 4) * 4)  # round up to a multiple of 4 -> integer gridlines
    step = (RIGHT - LEFT) / (len(days) - 1)

    def px(i: int) -> float:
        return LEFT + i * step

    def py(v: float) -> float:
        return BOTTOM - (BOTTOM - TOP) * v / y_max

    pts = [(px(i), py(c)) for i, (_, c) in enumerate(days)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{LEFT},{BOTTOM} {line} {RIGHT},{BOTTOM}"
    total = sum(c for _, c in days)
    first, last = days[0][0], days[-1][0]

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}" role="img" aria-label="{LOGIN} contribution graph, last {DAYS} days">',
        f"<title>{LOGIN}'s contributions, {first:%d %b} - {last:%d %b %Y}: {total}</title>",
        "<style>@keyframes draw{from{stroke-dashoffset:2400}}@keyframes fade{from{opacity:0}}"
        ".line{stroke-dasharray:2400;animation:draw 1.6s ease-out both}"
        ".fade{animation:fade .8s ease-out .6s both}"
        "@media (prefers-reduced-motion:reduce){.line,.fade{animation:none}}</style>",
        f'<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{LINE}" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="{LINE}" stop-opacity="0"/></linearGradient></defs>',
        f'<rect width="{W}" height="{H}" rx="8" fill="{BG}"/>',
        f'<text x="{W / 2}" y="38" text-anchor="middle" font-size="22" font-weight="600" fill="{TITLE}">'
        f"{LOGIN}'s Contribution Graph</text>",
    ]
    for k in range(5):
        v = y_max * k / 4
        y = py(v)
        out.append(f'<line x1="{LEFT}" y1="{y:.1f}" x2="{RIGHT}" y2="{y:.1f}" stroke="{GRID}" '
                   f'stroke-dasharray="{"0" if k == 0 else "4 4"}"/>')
        out.append(f'<text x="{LEFT - 12}" y="{y + 4:.1f}" text-anchor="end" font-size="12" '
                   f'fill="{TEXT}">{int(v)}</text>')
    for i, (day, _) in enumerate(days):
        out.append(f'<text x="{px(i):.1f}" y="{BOTTOM + 22}" text-anchor="middle" font-size="12" '
                   f'fill="{TEXT}">{day.day}</text>')
    out += [
        f'<text x="{(LEFT + RIGHT) / 2}" y="{H - 18}" text-anchor="middle" font-size="13" fill="{TEXT}">'
        f"Days ({first:%d %b} - {last:%d %b %Y})</text>",
        f'<text x="22" y="{(TOP + BOTTOM) / 2}" text-anchor="middle" font-size="13" fill="{TEXT}" '
        f'transform="rotate(-90 22 {(TOP + BOTTOM) / 2})">Contributions</text>',
        f'<polygon class="fade" points="{area}" fill="url(#area)"/>',
        f'<polyline class="line" points="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>',
        '<g class="fade">',
        *(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{POINT}"/>' for x, y in pts),
        "</g></svg>",
    ]
    return "".join(out)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: activity_graph.py OUTPUT.svg")
    path = sys.argv[1]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(fetch_days()) + "\n")


if __name__ == "__main__":
    main()
