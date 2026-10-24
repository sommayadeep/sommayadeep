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
    loop = 12
    lines = [
        f'<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">Neural Constellation contribution game</title>",
        "<desc id=\"desc\">An animated constellation built from GitHub contribution activity.</desc>",
        """<defs>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="smallGlow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="1.1" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <linearGradient id="nebula" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#071b2b"/>
    <stop offset="0.55" stop-color="#0b1624"/>
    <stop offset="1" stop-color="#12132a"/>
  </linearGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">
    <stop stop-color="#39e6c0" stop-opacity="0"/>
    <stop offset="0.5" stop-color="#b8fff0" stop-opacity="0.95"/>
    <stop offset="1" stop-color="#39e6c0" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="star">
    <stop stop-color="#e2fff8"/>
    <stop offset="0.3" stop-color="#62efd0"/>
    <stop offset="1" stop-color="#13a889" stop-opacity="0"/>
  </radialGradient>
</defs>""",
        f'<rect width="{SVG_W}" height="{SVG_H}" rx="10" fill="url(#nebula)"/>',
    ]

    # Tiny fixed stars make quiet weeks feel like space rather than empty UI.
    for _ in range(42):
        x = random.randint(10, SVG_W - 10)
        y = random.randint(35, SVG_H - 20)
        radius = random.choice((0.35, 0.5, 0.7))
        lines.append(
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="#93c5fd" opacity="{random.uniform(.12, .35):.2f}"/>'
        )

    lines += [
        f'<text x="{PAD_L}" y="23" font-family="JetBrains Mono,SFMono-Regular,Consolas,monospace" font-size="11" fill="#8fffe0" letter-spacing="1.5" filter="url(#smallGlow)">NEURAL_CONSTELLATION</text>',
        f'<text x="{SVG_W - PAD_L}" y="22" text-anchor="end" font-family="JetBrains Mono,SFMono-Regular,Consolas,monospace" font-size="9" fill="#65d9c0" opacity=".85">SIGNALS: {total}</text>',
        f'<text x="{PAD_L}" y="38" font-family="monospace" font-size="7" fill="#75a9bb" letter-spacing="1">GITHUB ACTIVITY // LIVE ORBITAL MAP</text>',
        f'<line x1="{PAD_L}" y1="44" x2="{SVG_W - PAD_L}" y2="44" stroke="#40d7b5" stroke-width=".5" opacity=".35"/>',
    ]

    for row, label in enumerate(("MON", "", "WED", "", "FRI", "", "SUN")):
        if label:
            y = PAD_T + row * STEP + 10
            lines.append(
                f'<text x="{PAD_L - 7}" y="{y}" text-anchor="end" font-family="monospace" font-size="6.5" fill="#71a5b2" opacity=".75">{label}</text>'
            )

    # Draw the calendar and let active nodes pulse at different phases.
    for col, week in enumerate(grid):
        for row, day in enumerate(week):
            x = PAD_L + col * STEP
            y = PAD_T + row * STEP
            count = day["count"]
            phase = (col * 0.071 + row * 0.13) % 1
            lines.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{level_color(count)}" opacity=".72"/>'
            )
            if count:
                color = signal_color(count)
                lines.append(
                    f'<circle cx="{x + CELL / 2:g}" cy="{y + CELL / 2:g}" r="2.1" fill="{color}" filter="url(#smallGlow)">'
                    f'<animate attributeName="r" values="1.5;3.8;1.5" dur="3.8s" begin="-{phase:.2f}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values=".45;1;.45" dur="3.8s" begin="-{phase:.2f}s" repeatCount="indefinite"/></circle>'
                )

    grid_left = PAD_L
    grid_right = PAD_L + GRID_W
    grid_mid_y = PAD_T + GRID_H / 2
    # A scanner sweeps horizontally; the glow trail makes it read like a game.
    lines += [
        f'<rect x="{grid_left - 20}" y="{PAD_T - 8}" width="80" height="{GRID_H + 16}" fill="url(#scan)" opacity="0" filter="url(#glow)">'
        f'<animate attributeName="x" values="{grid_left - 35};{grid_right - 35};{grid_left - 35}" dur="{loop}s" repeatCount="indefinite"/></rect>',
        f'<line x1="{grid_left}" y1="{grid_mid_y:g}" x2="{grid_right}" y2="{grid_mid_y:g}" stroke="#62dfc4" stroke-width=".5" stroke-dasharray="2 8" opacity=".18"/>',
        f'<circle cx="{grid_left}" cy="{grid_mid_y:g}" r="9" fill="none" stroke="#75f6d4" stroke-width="1.2" opacity=".75" filter="url(#smallGlow)">'
        f'<animate attributeName="cx" values="{grid_left};{grid_right};{grid_left}" dur="{loop}s" repeatCount="indefinite"/>'
        f'<animate attributeName="r" values="5;13;5" dur="{loop}s" repeatCount="indefinite"/></circle>',
        f'<circle cx="{grid_left}" cy="{grid_mid_y:g}" r="2.5" fill="#e2fff8" filter="url(#glow)">'
        f'<animate attributeName="cx" values="{grid_left};{grid_right};{grid_left}" dur="{loop}s" repeatCount="indefinite"/></circle>',
    ]

    bar_y = SVG_H - 27
    lines += [
        f'<line x1="{PAD_L}" y1="{bar_y - 13}" x2="{SVG_W - PAD_L}" y2="{bar_y - 13}" stroke="#40d7b5" stroke-width=".5" opacity=".3"/>',
        f'<text x="{PAD_L}" y="{bar_y}" font-family="monospace" font-size="8" fill="#75cdbb" letter-spacing=".5">ORBIT STATUS: NOMINAL</text>',
        f'<text x="{SVG_W - PAD_L}" y="{bar_y}" text-anchor="end" font-family="monospace" font-size="8" fill="#75cdbb">github.com/{USERNAME}</text>',
        f'<text x="{PAD_L}" y="{SVG_H - 9}" font-family="monospace" font-size="7" fill="#55798a">LOW</text>',
        f'<rect x="{PAD_L + 23}" y="{SVG_H - 15}" width="10" height="7" rx="2" fill="#123b35"/>',
        f'<rect x="{PAD_L + 37}" y="{SVG_H - 15}" width="10" height="7" rx="2" fill="#087f68"/>',
        f'<rect x="{PAD_L + 51}" y="{SVG_H - 15}" width="10" height="7" rx="2" fill="#18c29c"/>',
        f'<rect x="{PAD_L + 65}" y="{SVG_H - 15}" width="10" height="7" rx="2" fill="#73f5c5"/>',
        f'<text x="{PAD_L + 81}" y="{SVG_H - 9}" font-family="monospace" font-size="7" fill="#55798a">HIGH</text>',
    ]

    # Corner marks reinforce the instrument-panel feel without hiding data.
    corner = 6
    lines.append(f'<g fill="none" stroke="#55d8bd" stroke-width="1" opacity=".55"><path d="M{PAD_L-corner} 50V44h6 M{SVG_W-PAD_L+corner} 50V44h-6 M{PAD_L-corner} {SVG_H-5}v-6h6 M{SVG_W-PAD_L+corner} {SVG_H-5}v-6h-6"/></g>')
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
