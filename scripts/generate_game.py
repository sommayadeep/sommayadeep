"""
generate_game.py
Fetches real GitHub contribution data and generates a unique
"COMMIT CANNON" animated SVG — a laser cannon sweeps across the
contribution grid firing beams that activate each cell.
"""

import os
import json
import math
import random
import requests

# ── Config ──────────────────────────────────────────────────────────────
USERNAME = os.environ.get("GITHUB_USERNAME", "sommayadeep")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = "assets/contribution-game.svg"

# ── SVG layout ──────────────────────────────────────────────────────────
CELL    = 13      # cell size px
GAP     = 2       # gap between cells
STEP    = CELL + GAP
COLS    = 52      # weeks in a year
ROWS    = 7       # days per week
PAD_L   = 28
PAD_T   = 52
GRID_W  = COLS * STEP
GRID_H  = ROWS * STEP
SVG_W   = PAD_L + GRID_W + 28
SVG_H   = PAD_T + GRID_H + 56

# ── GitHub GraphQL ────────────────────────────────────────────────────────
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
    if not TOKEN:
        return None, 0
    try:
        r = requests.post(
            "https://api.github.com/graphql",
            json={"query": QUERY},
            headers={"Authorization": f"bearer {TOKEN}"},
            timeout=15,
        )
        data = r.json()
        cal  = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        weeks = cal["weeks"]
        total = cal["totalContributions"]
        # Build 52×7 grid (col=week, row=day)
        grid = []
        for week in weeks[:COLS]:
            col = []
            for day in week["contributionDays"]:
                col.append({
                    "count": day["contributionCount"],
                    "color": day["color"],
                })
            # Pad short columns
            while len(col) < ROWS:
                col.append({"count": 0, "color": "#161b22"})
            grid.append(col)
        # Pad missing weeks
        while len(grid) < COLS:
            grid.append([{"count": 0, "color": "#161b22"}] * ROWS)
        return grid, total
    except Exception as e:
        print(f"[warn] API fetch failed: {e}")
        return None, 0


def level_color(count):
    """Return green-scale hex based on contribution count."""
    if count == 0:   return "#161b22"
    if count <= 2:   return "#0e4429"
    if count <= 5:   return "#006d32"
    if count <= 10:  return "#26a641"
    return              "#39d353"


def beam_color(count):
    """Bright flash color for the cannon beam hit."""
    if count == 0:   return "#1a3a2a"
    if count <= 2:   return "#22c55e"
    if count <= 5:   return "#4ade80"
    if count <= 10:  return "#86efac"
    return              "#bbf7d0"


def make_svg(grid, total):
    random.seed(42)

    # ── Animation timing ────────────────────────────────────────────────
    # One full sweep = 8 s (loops forever)
    LOOP_DUR   = 8.0
    INTRO      = 0.4          # time before cannon starts moving
    COL_DT     = (LOOP_DUR - INTRO - 0.5) / COLS   # time per column ≈ 0.138 s
    ROW_DT     = 0.018        # delay between rows within a column
    FLASH_DUR  = 0.28         # how long the bright flash lasts
    SETTLE_DUR = 0.25         # fade-in to final color

    lines = []
    lines.append(f'<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg">')
    lines.append("<defs>")

    # Glow filter for cannon + beam
    lines.append("""
  <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="softglow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="1.2" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>""")

    # Gradient for cannon body
    lines.append("""
  <linearGradient id="cannonGrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#4ade80"/>
    <stop offset="100%" stop-color="#166534"/>
  </linearGradient>""")

    # Day-of-week labels
    days = ["Mon","","Wed","","Fri","","Sun"]
    lines.append("</defs>")

    # ── Background ──────────────────────────────────────────────────────
    lines.append(f'<rect width="{SVG_W}" height="{SVG_H}" fill="#0d1117" rx="8"/>')

    # Subtle scanline grid texture
    for yy in range(PAD_T, PAD_T + GRID_H, STEP):
        lines.append(f'<line x1="{PAD_L}" y1="{yy}" x2="{PAD_L+GRID_W}" y2="{yy}" stroke="#ffffff" stroke-width="0.15" opacity="0.04"/>')

    # ── HUD Top bar ──────────────────────────────────────────────────────
    # Title
    lines.append(f'<text x="{PAD_L}" y="22" font-family="JetBrains Mono,SFMono-Regular,Consolas,monospace" '
                 f'font-size="11" fill="#4ade80" letter-spacing="1.5" filter="url(#softglow)">'
                 f'COMMIT_CANNON.exe</text>')
    # Total contributions
    lines.append(f'<text x="{SVG_W - PAD_L}" y="22" font-family="JetBrains Mono,SFMono-Regular,Consolas,monospace" '
                 f'font-size="9" fill="#22c55e" text-anchor="end" opacity="0.8">'
                 f'TOTAL: {total} commits</text>')
    # Sub-title line
    lines.append(f'<line x1="{PAD_L}" y1="30" x2="{SVG_W-PAD_L}" y2="30" stroke="#10b981" stroke-width="0.5" opacity="0.3"/>')

    # Day labels
    for r, label in enumerate(days):
        if label:
            yy = PAD_T + r * STEP + CELL // 2 + 4
            lines.append(f'<text x="{PAD_L - 6}" y="{yy}" font-family="monospace" font-size="7" '
                         f'fill="#4ade80" text-anchor="end" opacity="0.5">{label}</text>')

    # ── Contribution cells ────────────────────────────────────────────────
    for c, week in enumerate(grid):
        x = PAD_L + c * STEP
        col_begin = INTRO + c * COL_DT   # when cannon reaches this column

        for r, day in enumerate(week):
            y = PAD_T + r * STEP
            base_col  = level_color(day["count"])
            flash_col = beam_color(day["count"])
            cell_begin = round(col_begin + r * ROW_DT, 3)

            # Each cell: starts dim, flashes bright when beam hits, settles
            # Use repeatCount="indefinite" so it loops with the overall animation

            # Base rect (always visible, dim)
            lines.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                         f'rx="2" fill="{base_col}" opacity="0.35"/>')

            # Animated overlay — flash then settle
            lines.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{flash_col}" opacity="0">'
                f'<animate attributeName="opacity" '
                f'  values="0;0;0.95;0.7;0" '
                f'  keyTimes="0;{cell_begin/LOOP_DUR:.4f};{(cell_begin+0.05)/LOOP_DUR:.4f};{(cell_begin+FLASH_DUR)/LOOP_DUR:.4f};{(cell_begin+FLASH_DUR+SETTLE_DUR)/LOOP_DUR:.4f}" '
                f'  dur="{LOOP_DUR}s" repeatCount="indefinite"/>'
                f'</rect>'
            )

            # After settle: keep cell at full brightness for the rest of the loop
            stay_start = cell_begin + FLASH_DUR + SETTLE_DUR
            if stay_start < LOOP_DUR - 0.5:
                lines.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{base_col}" opacity="0">'
                    f'<animate attributeName="opacity" '
                    f'  values="0;0;1;1;0" '
                    f'  keyTimes="0;{stay_start/LOOP_DUR:.4f};{(stay_start+0.05)/LOOP_DUR:.4f};{(LOOP_DUR-0.3)/LOOP_DUR:.4f};1" '
                    f'  dur="{LOOP_DUR}s" repeatCount="indefinite"/>'
                    f'</rect>'
                )

    # ── Cannon ────────────────────────────────────────────────────────────
    cannon_y  = PAD_T + GRID_H + 14  # sits below the grid
    beam_top  = PAD_T - 4

    # Cannon x-position: animates across columns
    # Use keyTimes evenly spaced across the sweep phase
    x_vals = []
    t_vals = []
    for c in range(COLS):
        cx = PAD_L + c * STEP + CELL // 2
        t  = (INTRO + c * COL_DT) / LOOP_DUR
        x_vals.append(str(cx))
        t_vals.append(f"{t:.4f}")
    # Hold at end, reset to start
    x_vals = [x_vals[0]] + x_vals + [x_vals[-1], x_vals[0]]
    t_vals = ["0"] + t_vals + [f"{(LOOP_DUR-0.3)/LOOP_DUR:.4f}", "1"]

    cannon_xs = ";".join(x_vals)
    cannon_ts = ";".join(t_vals)

    # Cannon barrel (rectangle that moves)
    lines.append(f'<g filter="url(#glow)">')
    # Barrel
    lines.append(
        f'<rect y="{cannon_y - 14}" width="8" height="14" rx="2" fill="url(#cannonGrad)" x="-4">'
        f'<animate attributeName="x" values="{cannon_xs}" keyTimes="{cannon_ts}" '
        f'  calcMode="linear" dur="{LOOP_DUR}s" repeatCount="indefinite" additive="sum"/>'
        f'</rect>'
    )
    # Cannon base
    lines.append(
        f'<rect y="{cannon_y}" width="18" height="8" rx="3" fill="#166534" x="-9">'
        f'<animate attributeName="x" values="{cannon_xs}" keyTimes="{cannon_ts}" '
        f'  calcMode="linear" dur="{LOOP_DUR}s" repeatCount="indefinite" additive="sum"/>'
        f'</rect>'
    )
    lines.append('</g>')

    # ── Beam (fires once per column) ──────────────────────────────────────
    # The beam is a tall thin rect that appears briefly at the current column
    beam_h = cannon_y - beam_top
    beam_x_vals = []
    beam_t_vals = []
    opac_vals   = []

    for c in range(COLS):
        bx = PAD_L + c * STEP + CELL // 2 - 1
        t_fire  = (INTRO + c * COL_DT) / LOOP_DUR
        t_end   = t_fire + (ROWS * ROW_DT + 0.12) / LOOP_DUR
        beam_x_vals.append(bx)
        beam_t_vals.append(t_fire)

    # Build full opacity keyframe sequence: flash on at each column, off in between
    op_seq  = []
    kt_seq  = []
    bx_seq  = []
    op_seq.append("0"); kt_seq.append("0"); bx_seq.append(str(beam_x_vals[0]))
    for i, c in enumerate(range(COLS)):
        t_fire = (INTRO + c * COL_DT) / LOOP_DUR
        t_off  = t_fire + (ROWS * ROW_DT + 0.10) / LOOP_DUR
        bx     = str(beam_x_vals[i])
        op_seq += ["0", "0.9", "0.9", "0"]
        kt_seq += [f"{max(t_fire-0.001,0):.4f}", f"{t_fire:.4f}", f"{min(t_off,0.9999):.4f}", f"{min(t_off+0.01,0.9999):.4f}"]
        bx_seq += [bx, bx, bx, bx]
    op_seq.append("0"); kt_seq.append("1"); bx_seq.append(str(beam_x_vals[-1]))

    op_str = ";".join(op_seq)
    kt_str = ";".join(kt_seq)
    bx_str = ";".join(bx_seq)

    lines.append(f'<rect y="{beam_top}" width="3" height="{beam_h}" fill="#4ade80" opacity="0" filter="url(#glow)">')
    lines.append(f'  <animate attributeName="x" values="{bx_str}" keyTimes="{kt_str}" dur="{LOOP_DUR}s" repeatCount="indefinite" calcMode="discrete"/>')
    lines.append(f'  <animate attributeName="opacity" values="{op_str}" keyTimes="{kt_str}" dur="{LOOP_DUR}s" repeatCount="indefinite" calcMode="discrete"/>')
    lines.append('</rect>')

    # Beam core (brighter center stripe)
    lines.append(f'<rect y="{beam_top}" width="1" height="{beam_h}" fill="#bbf7d0" opacity="0">')
    lines.append(f'  <animate attributeName="x" values="{bx_str}" keyTimes="{kt_str}" dur="{LOOP_DUR}s" repeatCount="indefinite" calcMode="discrete"/>')
    lines.append(f'  <animate attributeName="opacity" values="{op_str}" keyTimes="{kt_str}" dur="{LOOP_DUR}s" repeatCount="indefinite" calcMode="discrete"/>')
    lines.append('</rect>')

    # ── Bottom status bar ─────────────────────────────────────────────────
    bar_y = SVG_H - 10
    lines.append(f'<line x1="{PAD_L}" y1="{SVG_H-22}" x2="{SVG_W-PAD_L}" y2="{SVG_H-22}" stroke="#10b981" stroke-width="0.5" opacity="0.3"/>')
    lines.append(f'<text x="{PAD_L}" y="{bar_y}" font-family="JetBrains Mono,monospace" font-size="8" fill="#4ade80" opacity="0.6" letter-spacing="0.5">'
                 f'github.com/sommayadeep</text>')
    lines.append(f'<text x="{SVG_W-PAD_L}" y="{bar_y}" font-family="JetBrains Mono,monospace" font-size="8" fill="#4ade80" opacity="0.6" text-anchor="end">'
                 f'© {USERNAME}</text>')

    # Corner brackets
    b = 5
    lines.append(f'<g stroke="#10b981" stroke-width="1.2" fill="none" opacity="0.4">')
    lines.append(f'  <path d="M{PAD_L-b} {36+b} L{PAD_L-b} {36} L{PAD_L} {36}"/>')
    lines.append(f'  <path d="M{SVG_W-PAD_L+b} {36+b} L{SVG_W-PAD_L+b} {36} L{SVG_W-PAD_L} {36}"/>')
    lines.append(f'  <path d="M{PAD_L-b} {SVG_H-b-4} L{PAD_L-b} {SVG_H-4} L{PAD_L} {SVG_H-4}"/>')
    lines.append(f'  <path d="M{SVG_W-PAD_L+b} {SVG_H-b-4} L{SVG_W-PAD_L+b} {SVG_H-4} L{SVG_W-PAD_L} {SVG_H-4}"/>')
    lines.append('</g>')

    lines.append('</svg>')
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"[*] Fetching contributions for {USERNAME}...")
    grid, total = fetch_contributions()

    if grid is None:
        print("[!] Using placeholder data (no API token or error).")
        import random as _r
        _r.seed(0)
        grid = []
        for _ in range(COLS):
            week = []
            for __ in range(ROWS):
                c = _r.choices([0,1,3,6,12], weights=[40,25,20,10,5])[0]
                week.append({"count": c, "color": ""})
            grid.append(week)
        total = sum(d["count"] for w in grid for d in w)

    print(f"[*] Total contributions: {total}")
    svg = make_svg(grid, total)
    os.makedirs("assets", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"[✓] Written → {OUT_PATH}  ({len(svg):,} bytes)")
