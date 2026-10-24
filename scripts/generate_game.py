"""
Generate the animated "NEURAL CONSTELLATION" contribution game.

The contribution calendar is rendered as a constellation: every contribution
is a signal node, and an orbiting scanner periodically wakes the network.
The output is self-contained SVG so it remains animated in a GitHub README.
"""

import os
import random
import re
import math
from datetime import date, timedelta
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont


USERNAME = os.environ.get("GITHUB_USERNAME", "sommayadeep")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = "assets/contribution-game.gif"

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
    """Render a real frame-by-frame arcade game that GitHub plays as a GIF."""
    random.seed(7)
    frames = []
    frame_count = 24
    ship_y = PAD_T + GRID_H + 17
    active = [
        (col, row, day["count"])
        for col, week in enumerate(grid)
        for row, day in enumerate(week)
        if day["count"]
    ]
    stars = [(random.randrange(SVG_W), random.randrange(45, SVG_H - 25)) for _ in range(55)]
    font = ImageFont.load_default()

    for frame_no in range(frame_count):
        image = Image.new("RGB", (SVG_W, SVG_H), "#0b0d18")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, SVG_W - 1, SVG_H - 1), radius=10, fill="#0d1020", outline="#3b1c3d")
        for x, y in stars:
            draw.point((x, y), fill="#71658a")

        draw.text((PAD_L, 14), "COMMIT DEFENDER", fill="#ffd35a", font=font)
        draw.text((SVG_W - PAD_L - 92, 14), f"SCORE {total:04d}", fill="#ff6684", font=font)
        draw.text((PAD_L, 29), "REAL CONTRIBUTIONS // WAVE 01", fill="#b88fc9", font=font)
        draw.text((SVG_W - PAD_L - 75, 29), f"TARGETS {len(active):03d}", fill="#ffd35a", font=font)
        draw.line((PAD_L, 43, SVG_W - PAD_L, 43), fill="#8a3153", width=1)

        for row, label in enumerate(("MON", "", "WED", "", "FRI", "", "SUN")):
            if label:
                draw.text((5, PAD_T + row * STEP + 3), label, fill="#b88fc9", font=font)

        for col, week in enumerate(grid):
            for row, day in enumerate(week):
                x, y, count = PAD_L + col * STEP, PAD_T + row * STEP, day["count"]
                draw.rounded_rectangle((x, y, x + CELL, y + CELL), radius=3, fill=level_color(count))

        ship_x = PAD_L + 15 + int((GRID_W - 30) * (0.5 + 0.5 * math.sin(frame_no / frame_count * math.tau)))
        for index, (col, row, count) in enumerate(active):
            target_x = PAD_L + col * STEP + CELL // 2
            target_y = PAD_T + row * STEP + CELL // 2
            hit_frame = (col * 3 + row * 5) % frame_count
            distance = (frame_no - hit_frame) % frame_count
            if distance < 7:
                progress = min(1, distance / 4)
                laser_y = ship_y - (ship_y - target_y) * progress
                draw.line((ship_x, ship_y - 7, target_x, laser_y), fill="#ffb52e", width=2)
                if distance >= 4:
                    radius = 3 + (distance - 4) * 3
                    draw.ellipse((target_x - radius, target_y - radius, target_x + radius, target_y + radius), outline="#fff1a8", width=2)

        ship = [(ship_x - 13, ship_y + 7), (ship_x, ship_y - 9), (ship_x + 13, ship_y + 7), (ship_x + 5, ship_y + 5), (ship_x, ship_y + 11), (ship_x - 5, ship_y + 5)]
        draw.polygon(ship, fill="#ff7955", outline="#ffd35a")
        draw.line((ship_x, ship_y - 7, ship_x, PAD_T - 2), fill="#fff1a8", width=1)
        draw.line((PAD_L, ship_y + 12, PAD_L + GRID_W, ship_y + 12), fill="#8a3153", width=1)
        draw.text((PAD_L, SVG_H - 23), "HULL 100%", fill="#ff9a9f", font=font)
        draw.text((SVG_W // 2 - 68, SVG_H - 23), "LASER ONLINE", fill="#ffd35a", font=font)
        draw.text((SVG_W - PAD_L - 60, SVG_H - 23), USERNAME, fill="#ff9a9f", font=font)
        draw.text((PAD_L, SVG_H - 11), "COMMIT POWER", fill="#85658f", font=font)
        draw.rounded_rectangle((PAD_L + 72, SVG_H - 12, PAD_L + 170, SVG_H - 6), radius=3, fill="#35162d")
        draw.rounded_rectangle((PAD_L + 72, SVG_H - 12, PAD_L + 125 + (frame_no % 8) * 6, SVG_H - 6), radius=3, fill="#ff536d")
        frames.append(image)

    os.makedirs("assets", exist_ok=True)
    frames[0].save(OUT_PATH, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=False)
    return len(frames)


if __name__ == "__main__":
    print(f"[*] Fetching contributions for {USERNAME}...")
    grid, total = fetch_contributions()

    frame_count = make_gif(grid, total)
    os.makedirs("assets", exist_ok=True)
    print(f"[✓] Total contributions: {total}")
    print(f"[✓] Written → {OUT_PATH} ({frame_count} animated frames)")
