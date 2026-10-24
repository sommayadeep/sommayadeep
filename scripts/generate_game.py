"""
Generate the animated "NEURAL CONSTELLATION" contribution game.

The contribution calendar is rendered as a constellation: every contribution
is a signal node, and an orbiting scanner periodically wakes the network.
The output is self-contained SVG so it remains animated in a GitHub README.
"""

import os
import random
import re
from datetime import date, timedelta
import requests


USERNAME = os.environ.get("GITHUB_USERNAME", "sommayadeep")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = "assets/contribution-game.svg"

CELL = 13
GAP = 2
STEP = CELL + GAP
COLS = 52
ROWS = 7
PAD_L = 30
PAD_T = 56
GRID_W = COLS * STEP
GRID_H = ROWS * STEP
SVG_W = PAD_L + GRID_W + 30
SVG_H = PAD_T + GRID_H + 64

QUERY = """
{
  user(login: "%s") {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
""" % USERNAME


def fetch_contributions():
    if TOKEN:
        try:
            response = requests.post(
                "https://api.github.com/graphql",
                json={"query": QUERY},
                headers={"Authorization": f"bearer {TOKEN}"},
                timeout=15,
            )
            response.raise_for_status()
            calendar = response.json()["data"]["user"]["contributionsCollection"][
                "contributionCalendar"
            ]
            return normalize_days(
                [
                    (day["date"], day["contributionCount"])
                    for week in calendar["weeks"]
                    for day in week["contributionDays"]
                ],
                calendar["totalContributions"],
            )
        except (KeyError, TypeError, ValueError, requests.RequestException) as error:
            print(f"[warn] GraphQL fetch failed: {error}")

    # GitHub renders the same real calendar publicly, so local generation does
    # not need a token and never has to invent contribution data.
    try:
        response = requests.get(
            f"https://github.com/users/{USERNAME}/contributions",
            timeout=15,
        )
        response.raise_for_status()
        page = response.text
        total_match = re.search(
            r'id="js-contribution-activity-description"[^>]*>\s*([\d,]+)',
            page,
        )
        if not total_match:
            raise ValueError("public calendar total was not found")
        cells = re.findall(
            r'<td[^>]*data-date="([^"]+)"[^>]*data-level="(\d+)"[^>]*></td>'
            r'\s*<tool-tip[^>]*>(.*?)</tool-tip>',
            page,
            flags=re.DOTALL,
        )
        if not cells:
            raise ValueError("public calendar cells were not found")
        days = []
        for day_date, level, tooltip in cells:
            count_match = re.search(r"(\d[\d,]*) contributions?", tooltip)
            count = int(count_match.group(1).replace(",", "")) if count_match else 0
            days.append((day_date, count if count else int(level) and level_count(int(level))))
        return normalize_days(days, int(total_match.group(1).replace(",", "")))
    except (ValueError, requests.RequestException) as error:
        raise RuntimeError(f"unable to fetch real GitHub contributions: {error}") from error


def level_count(level):
    """Keep the public calendar useful if GitHub omits tooltip text."""
    return (0, 1, 3, 6, 12)[min(level, 4)]


def normalize_days(days, total):
    """Turn dated contribution cells into the fixed 52 x 7 game grid."""
    parsed = {(date.fromisoformat(day_date), count) for day_date, count in days}
    latest = max(day_date for day_date, _ in parsed)
    first_week = latest - timedelta(days=latest.weekday() + 7 * (COLS - 1))
    grid = []
    for week in range(COLS):
        column = []
        week_start = first_week + timedelta(days=week * 7)
        for row in range(ROWS):
            count = next(
                (value for day_date, value in parsed if day_date == week_start + timedelta(days=row)),
                0,
            )
            column.append({"count": count, "color": ""})
        grid.append(column)
    return grid, total


def level_color(count):
    if count == 0:
        return "#111827"
    if count <= 2:
        return "#123b35"
    if count <= 5:
        return "#087f68"
    if count <= 10:
        return "#18c29c"
    return "#73f5c5"


def signal_color(count):
    if count == 0:
        return "#1a3140"
    if count <= 2:
        return "#36d7b4"
    if count <= 5:
        return "#7df5d3"
    return "#d2fff1"


def make_svg(grid, total):
    random.seed(7)
    loop = 10
    ship_y = PAD_T + GRID_H + 17
    lines = [
        f'<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">Commit Defender contribution shooting game</title>",
        "<desc id=\"desc\">A shooting game where real GitHub contributions become targets and the commit defender fires at them.</desc>",
        """<defs>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <linearGradient id="space" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#090d20"/><stop offset=".55" stop-color="#10132c"/><stop offset="1" stop-color="#210e2b"/>
  </linearGradient>
  <linearGradient id="laser" x1="0" y1="0" x2="0" y2="1">
    <stop stop-color="#fff7b1"/><stop offset=".35" stop-color="#ffb52e"/><stop offset="1" stop-color="#ff3d81" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="ship" x1="0" y1="0" x2="0" y2="1">
    <stop stop-color="#ffe27a"/><stop offset="1" stop-color="#ff5b45"/>
  </linearGradient>
</defs>""",
        f'<rect width="{SVG_W}" height="{SVG_H}" rx="10" fill="url(#space)"/>',
    ]

    for _ in range(48):
        x = random.randint(8, SVG_W - 8)
        y = random.randint(35, SVG_H - 15)
        lines.append(f'<circle cx="{x}" cy="{y}" r="{random.choice((.3, .5, .8))}" fill="#b9c9ff" opacity="{random.uniform(.15, .5):.2f}"/>')

    lines += [
        f'<text x="{PAD_L}" y="23" font-family="JetBrains Mono,SFMono-Regular,Consolas,monospace" font-size="11" fill="#ffcf56" letter-spacing="1.5" filter="url(#glow)">COMMIT_DEFENDER</text>',
        f'<text x="{SVG_W - PAD_L}" y="22" text-anchor="end" font-family="monospace" font-size="9" fill="#ff7698">SCORE: {total:04d}</text>',
        f'<text x="{PAD_L}" y="38" font-family="monospace" font-size="7" fill="#c59bd4" letter-spacing="1">WAVE 01 // REAL GITHUB CONTRIBUTIONS</text>',
        f'<text x="{SVG_W - PAD_L}" y="38" text-anchor="end" font-family="monospace" font-size="7" fill="#ffcf56">TARGETS: {sum(day["count"] > 0 for week in grid for day in week):03d}</text>',
        f'<line x1="{PAD_L}" y1="44" x2="{SVG_W - PAD_L}" y2="44" stroke="#ff5f78" stroke-width=".5" opacity=".5"/>',
    ]

    for row, label in enumerate(("MON", "", "WED", "", "FRI", "", "SUN")):
        if label:
            lines.append(f'<text x="{PAD_L - 7}" y="{PAD_T + row * STEP + 10}" text-anchor="end" font-family="monospace" font-size="6.5" fill="#ad91c6">{label}</text>')

    for col, week in enumerate(grid):
        for row, day in enumerate(week):
            x, y, count = PAD_L + col * STEP, PAD_T + row * STEP, day["count"]
            color = level_color(count)
            lines.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{color}" opacity=".8"/>')
            if count:
                cx, cy = x + CELL / 2, y + CELL / 2
                phase = (col * .09 + row * .17) % 1
                # Every active contribution is a target that gets hit by a laser.
                lines.append(
                    f'<circle cx="{cx:g}" cy="{cy:g}" r="3" fill="{signal_color(count)}" filter="url(#glow)">'
                    f'<animate attributeName="r" values="2;5;2" dur="2.4s" begin="-{phase:.2f}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values=".55;1;.55" dur="2.4s" begin="-{phase:.2f}s" repeatCount="indefinite"/></circle>'
                )
                lines.append(
                    f'<path d="M{cx:g} {ship_y} L{cx:g} {cy:g}" stroke="url(#laser)" stroke-width="1.5" opacity=".12" filter="url(#glow)">'
                    f'<animate attributeName="opacity" values=".12;1;.12" dur="{loop}s" begin="{(col * .16 + row * .025):.2f}s" repeatCount="indefinite"/></path>'
                )
                lines.append(
                    f'<circle cx="{cx:g}" cy="{cy:g}" r="2" fill="none" stroke="#fff1a8" opacity=".25">'
                    f'<animate attributeName="r" values="2;11;2" dur="{loop}s" begin="{(col * .16 + row * .025 + .08):.2f}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values=".25;1;.25" dur="{loop}s" begin="{(col * .16 + row * .025 + .08):.2f}s" repeatCount="indefinite"/></circle>'
                )

    # The defender tracks the latest active column while firing upward.
    lines += [
        f'<path d="M{PAD_L} {ship_y + 8} H{PAD_L + GRID_W}" stroke="#ff4f68" stroke-width="1" stroke-dasharray="2 5" opacity=".45"/>',
        f'<g transform="translate({PAD_L + 20},0)" filter="url(#glow)">'
        f'<animateTransform attributeName="transform" type="translate" values="{PAD_L + 20},0;{PAD_L + GRID_W - 20},0;{PAD_L + 20},0" dur="{loop}s" repeatCount="indefinite"/>'
        f'<path d="M-13 {ship_y + 7} L0 {ship_y - 8} L13 {ship_y + 7} L7 {ship_y + 5} L0 {ship_y + 11} L-7 {ship_y + 5} Z" fill="url(#ship)"/>'
        f'<path d="M0 {ship_y - 7} V{PAD_T - 2}" stroke="#fff1a8" stroke-width="2" opacity=".9">'
        f'<animate attributeName="opacity" values=".35;1;.35" dur="1.1s" repeatCount="indefinite"/></path></g>',
    ]

    bar_y = SVG_H - 25
    lines += [
        f'<line x1="{PAD_L}" y1="{bar_y - 12}" x2="{SVG_W - PAD_L}" y2="{bar_y - 12}" stroke="#ff5f78" stroke-width=".5" opacity=".5"/>',
        f'<text x="{PAD_L}" y="{bar_y}" font-family="monospace" font-size="8" fill="#ff9a9f">HULL: 100%</text>',
        f'<text x="{SVG_W / 2:g}" y="{bar_y}" text-anchor="middle" font-family="monospace" font-size="8" fill="#ffcf56">LASER ONLINE // FIRE AT THE WORK</text>',
        f'<text x="{SVG_W - PAD_L}" y="{bar_y}" text-anchor="end" font-family="monospace" font-size="8" fill="#ff9a9f">{USERNAME}</text>',
        f'<text x="{PAD_L}" y="{SVG_H - 8}" font-family="monospace" font-size="7" fill="#85658f">COMMIT POWER</text>',
        f'<rect x="{PAD_L + 68}" y="{SVG_H - 14}" width="90" height="6" rx="3" fill="#35162d"/>',
        f'<rect x="{PAD_L + 68}" y="{SVG_H - 14}" width="{min(90, max(4, total / max(total, 1) * 90)):.1f}" height="6" rx="3" fill="#ff536d"><animate attributeName="width" values="20;90;20" dur="3s" repeatCount="indefinite"/></rect>',
    ]
    lines.append(f'<g fill="none" stroke="#ff6b7e" stroke-width="1" opacity=".65"><path d="M{PAD_L-6} 50V44h6 M{SVG_W-PAD_L+6} 50V44h-6 M{PAD_L-6} {SVG_H-5}v-6h6 M{SVG_W-PAD_L+6} {SVG_H-5}v-6h-6"/></g>')
    lines.append("</svg>")
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"[*] Fetching contributions for {USERNAME}...")
    grid, total = fetch_contributions()

    svg = make_svg(grid, total)
    os.makedirs("assets", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as output:
        output.write(svg)
    print(f"[✓] Total contributions: {total}")
    print(f"[✓] Written → {OUT_PATH} ({len(svg):,} bytes)")
