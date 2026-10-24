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
from PIL import Image, ImageDraw, ImageFont


USERNAME = os.environ.get("GITHUB_USERNAME", "sommayadeep")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = "assets/contribution-graph.gif"

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


def make_gif(grid, total):
    """Render a restrained, frame-by-frame contribution graph reveal."""
    frames = []
    frame_count = COLS + 8
    font = ImageFont.load_default()

    for frame_no in range(frame_count):
        image = Image.new("RGB", (SVG_W, SVG_H), "#0d1117")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, SVG_W - 1, SVG_H - 1), radius=10, fill="#0d1117", outline="#30363d")
        draw.text((PAD_L, 14), f"{total:,} contributions", fill="#f0f6fc", font=font)
        draw.text((SVG_W - PAD_L - 105, 14), f"@{USERNAME}", fill="#8b949e", font=font)
        draw.text((PAD_L, 30), "Less", fill="#8b949e", font=font)
        draw.text((SVG_W - PAD_L - 25, 30), "More", fill="#8b949e", font=font)
        for level, color in enumerate(("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")):
            x = SVG_W - PAD_L - 70 + level * 15
            draw.rounded_rectangle((x, 29, x + 11, 40), radius=2, fill=color)

        revealed_col = min(COLS, frame_no)
        for col, week in enumerate(grid):
            for row, day in enumerate(week):
                x, y = PAD_L + col * STEP, PAD_T + row * STEP
                fill = level_color(day["count"]) if col < revealed_col else "#161b22"
                draw.rounded_rectangle((x, y, x + CELL, y + CELL), radius=2, fill=fill)

        if revealed_col < COLS:
            sweep_x = PAD_L + revealed_col * STEP + CELL // 2
            draw.line((sweep_x, PAD_T - 5, sweep_x, PAD_T + GRID_H + 5), fill="#58a6ff", width=1)
        else:
            draw.line((PAD_L, PAD_T + GRID_H + 13, PAD_L + GRID_W, PAD_T + GRID_H + 13), fill="#30363d", width=1)
            draw.text((PAD_L, SVG_H - 22), "updated from GitHub contribution activity", fill="#8b949e", font=font)
            draw.text((SVG_W - PAD_L - 62, SVG_H - 22), "github.com", fill="#58a6ff", font=font)
        frames.append(image)

    os.makedirs("assets", exist_ok=True)
    frames[0].save(OUT_PATH, save_all=True, append_images=frames[1:], duration=55, loop=0, optimize=False)
    return len(frames)


if __name__ == "__main__":
    print(f"[*] Fetching contributions for {USERNAME}...")
    grid, total = fetch_contributions()

    frame_count = make_gif(grid, total)
    os.makedirs("assets", exist_ok=True)
    print(f"[✓] Total contributions: {total}")
    print(f"[✓] Written → {OUT_PATH} ({frame_count} animated frames)")
