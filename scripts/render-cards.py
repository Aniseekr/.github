"""Render the org profile cards (profile/header.svg, profile/panels.svg).

Brand sources come from the landing repo (aniseekr.moe v6): the lockup, the
Seekr poses. Fonts are subset to the glyphs used and inlined, because GitHub
shows SVGs through <img>, which cannot load web fonts.

  python scripts/render-cards.py <landing-repo> <fonts-dir>

<fonts-dir> holds Bangers-Regular.ttf, ZenKakuGothicNew-Black.ttf and
Nunito-ExtraBold.ttf (all OFL, from github.com/google/fonts).
"""

import base64
import io
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from fontTools import subset

LANDING, FONTS = Path(sys.argv[1]), Path(sys.argv[2])
OUT = Path(__file__).resolve().parent.parent / "profile"

INK, PAPER, ORANGE, LEMON, CARD = "#080808", "#F4F1EA", "#FF9F0A", "#FFD966", "#0B0B0C"

HEADER_TEXT = {
    "Bangers": "ANIME TRACKER · PILGRIMAGE COMPANION",
    "Nunito": "Track every anime. Visit every scene.iOS · Android · aniseekr.moe",
    "Zen": "番，交給我找。",
}
PANELS = [
    ("01", "TRACK", ["7 sources, one library.", "Two-way sync, or stay offline."], "phone"),
    ("02", "AIRING", ["This season's schedule,", "with episode reminders."], "read"),
    ("03", "VISIT", ["Scene map, trip planner,", "and a shot-matching camera."], "camera"),
]

# height / width of each pose image, so it is never squashed
POSE_RATIO = {"phone": 640 / 548, "read": 613 / 560, "camera": 625 / 560, "wave": 581 / 560}


def font_face(family: str, file: str, text: str) -> str:
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    font = subset.load_font(str(FONTS / file), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    buf = io.BytesIO()
    subset.save_font(font, buf, opts)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face {{ font-family: '{family}'; src: url(data:font/woff2;base64,{b64}) format('woff2'); }}"


def fonts(bangers: str, nunito: str, zen: str = "") -> str:
    faces = [
        font_face("Bangers", "Bangers-Regular.ttf", bangers),
        font_face("Nunito", "Nunito-ExtraBold.ttf", nunito),
    ]
    if zen:
        faces.append(font_face("Zen", "ZenKakuGothicNew-Black.ttf", zen))
    return f"<style><![CDATA[{''.join(faces)}]]></style>"


def pose(name: str, width: int) -> str:
    """A Seekr pose as an inline webp, resized to `width` px (2x for retina)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "p.webp"
        subprocess.run(
            ["cwebp", "-quiet", "-q", "82", "-alpha_q", "90", "-resize", str(width * 2), "0",
             str(LANDING / "static/seekr" / f"{name}.webp"), "-o", str(out)],
            check=True,
        )
        return "data:image/webp;base64," + base64.b64encode(out.read_bytes()).decode()


def lockup() -> str:
    """The night lockup without its backdrop; the EE pupils glance around."""
    svg = (LANDING / "static/brand/lockup-night.svg").read_text()
    body = re.sub(r"^<svg[^>]*>|</svg>$", "", svg.strip())
    body = re.sub(r'<rect x="-12" y="-14"[^>]*/>', "", body, count=1)
    body = body.replace('id="hc"', 'id="lk-hc"').replace("url(#hc)", "url(#lk-hc)")
    body = body.replace('id="ec"', 'id="lk-ec"').replace("url(#ec)", "url(#lk-ec)")
    glance = (
        '<animateTransform attributeName="transform" type="translate" '
        'values="0 0;0 0;7 2;7 2;-7 2;-7 2;0 0" keyTimes="0;0.5;0.56;0.7;0.76;0.9;1" '
        'dur="7s" begin="1.4s" repeatCount="indefinite"/>'
    )

    def eye(m: re.Match) -> str:
        cx = m.group(1)
        return (
            f"<g>{glance}"
            f'<circle cx="{cx}" cy="40.0" r="22" fill="{LEMON}"/>'
            f'<circle cx="{cx}" cy="40.0" r="12" fill="#0B0C10"/>'
            f'<circle cx="{float(cx) - 5:.2f}" cy="34.0" r="4" fill="#fff"/></g>'
        )

    return re.sub(
        r'<circle cx="([\d.]+)" cy="40.0" r="22" fill="#FFD966"/>'
        r'<circle cx="[\d.]+" cy="40.0" r="12" fill="#0B0C10"/>'
        r'<circle cx="[\d.]+" cy="34.0" r="4" fill="#fff"/>',
        eye,
        body,
    )


def halftone(cx: float, cy: float, reach: float, step: float, rmax: float, color: str) -> str:
    dots = []
    for row in range(-int(reach / step), int(reach / step) + 1):
        for col in range(-int(reach / step), int(reach / step) + 1):
            x = cx + col * step + (step / 2 if row % 2 else 0)
            y = cy + row * step * 0.87
            d = math.hypot(x - cx, y - cy) / reach
            if d < 1:
                r = rmax * (1 - d) ** 1.3
                if r > 0.5:
                    dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}"/>')
    return f'<g fill="{color}">{"".join(dots)}</g>'


def focus_lines(cx: float, cy: float, inner: float, outer: float, n: int, seed: int) -> str:
    """Manga speed lines radiating from (cx, cy), as thin wedges."""
    paths = []
    for i in range(n):
        a = 2 * math.pi * i / n + math.sin(i * 12.9898 + seed) * 0.05
        r0 = inner + (math.sin(i * 78.233 + seed) * 0.5 + 0.5) * inner * 0.6
        w = 0.008 + (math.sin(i * 3.1 + seed) * 0.5 + 0.5) * 0.012
        x0, y0 = cx + r0 * math.cos(a), cy + r0 * math.sin(a)
        x1, y1 = cx + outer * math.cos(a - w), cy + outer * math.sin(a - w)
        x2, y2 = cx + outer * math.cos(a + w), cy + outer * math.sin(a + w)
        paths.append(f"M{x0:.1f} {y0:.1f}L{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}Z")
    return "".join(paths)


def header() -> str:
    W, H = 900, 240
    sx, sy = 742, 118  # Seekr's centre: halftone and focus lines radiate from here
    lines_a = focus_lines(sx, sy, 120, 700, 64, 1)
    lines_b = focus_lines(sx, sy, 120, 700, 64, 7)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Aniseekr — track every anime, visit every scene">
  <title>Aniseekr</title>
  <!-- generated by scripts/render-cards.py — edit the script, not this file -->
  <defs>
    {fonts(HEADER_TEXT["Bangers"], HEADER_TEXT["Nunito"], HEADER_TEXT["Zen"])}
    <clipPath id="card"><rect x="2" y="2" width="{W - 12}" height="{H - 12}"/></clipPath>
    <clipPath id="wipe">
      <rect x="20" y="40" width="0" height="120">
        <animate attributeName="width" values="0;560" dur="0.8s" begin="0.2s" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1" fill="freeze"/>
      </rect>
    </clipPath>
  </defs>

  <rect x="8" y="8" width="{W - 8}" height="{H - 8}" fill="{ORANGE}"/>
  <rect x="1" y="1" width="{W - 10}" height="{H - 10}" fill="{CARD}" stroke="{PAPER}" stroke-width="2"/>
  <g clip-path="url(#card)">
    {halftone(sx, sy, 300, 13, 5.2, ORANGE)}
    <!-- two sets of speed lines swapped at ~8fps, like a held manga frame -->
    <path d="{lines_a}" fill="{PAPER}" fill-opacity="0.16">
      <animate attributeName="opacity" values="1;0" calcMode="discrete" dur="0.25s" repeatCount="indefinite"/>
    </path>
    <path d="{lines_b}" fill="{PAPER}" fill-opacity="0.16" opacity="0">
      <animate attributeName="opacity" values="0;1" calcMode="discrete" dur="0.25s" repeatCount="indefinite"/>
    </path>
    <rect width="470" height="{H}" fill="{CARD}" opacity="0.88"/>
    <path d="M470 0 L520 0 L470 {H} Z" fill="{CARD}" opacity="0.88"/>

    <!-- Seekr waves, bobbing, and hops every 6s -->
    <g transform="translate(0 0)">
      <animateTransform attributeName="transform" type="translate" values="0 0;0 0;0 -18;0 0;0 0" keyTimes="0;0.86;0.92;0.97;1" dur="6s" begin="2s" repeatCount="indefinite"/>
      <g>
        <animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0" dur="2.4s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>
        <image href="{pose("wave", 210)}" x="{sx - 105}" y="{sy - 102}" width="210" height="{int(210 * POSE_RATIO["wave"])}"/>
      </g>
    </g>
  </g>

  <!-- speech balloon pops in -->
  <g opacity="0">
    <animate attributeName="opacity" values="0;1" dur="0.01s" begin="1.1s" fill="freeze"/>
    <g transform="translate(560 58)">
      <animateTransform attributeName="transform" type="scale" values="0.4;1.12;1" keyTimes="0;0.6;1" dur="0.35s" begin="1.1s" fill="freeze" additive="sum"/>
      <path d="M-82 -26 Q-82 -38 -70 -38 L70 -38 Q82 -38 82 -26 L82 10 Q82 22 70 22 L40 22 L58 44 L14 22 L-70 22 Q-82 22 -82 10 Z" fill="#fff" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>
      <text x="0" y="0" text-anchor="middle" font-family="'Zen', 'Hiragino Sans', sans-serif" font-size="22" fill="{INK}">番，交給我找。</text>
    </g>
  </g>

  <g opacity="0">
    <animate attributeName="opacity" values="0;1" dur="0.5s" begin="0.1s" fill="freeze"/>
    <text x="34" y="46" font-family="'Bangers', Impact, sans-serif" font-size="18" letter-spacing="2.5" fill="{ORANGE}">ANIME TRACKER · PILGRIMAGE COMPANION</text>
  </g>
  <g clip-path="url(#wipe)">
    <g transform="translate(42 66) scale(0.62)">{lockup()}</g>
  </g>
  <g opacity="0">
    <animate attributeName="opacity" values="0;1" dur="0.5s" begin="0.8s" fill="freeze"/>
    <rect x="34" y="158" width="10" height="10" fill="{LEMON}"/>
    <text x="54" y="168" font-family="'Nunito', system-ui, sans-serif" font-weight="800" font-size="20" fill="{PAPER}">Track every anime. Visit every scene.</text>
    <text x="34" y="200" font-family="'Nunito', system-ui, sans-serif" font-weight="800" font-size="13" letter-spacing="1.5" fill="{PAPER}" fill-opacity="0.55">iOS · Android · aniseekr.moe</text>
  </g>
</svg>
"""


def panels() -> str:
    W, H = 900, 316
    top, bot = 14, H - 24
    # Gutters slant the same way, like two cuts across one manga page.
    cuts = [(14, 14), (300, 278), (594, 572), (876, 876)]
    bangers = "".join(p[0] + p[1] for p in PANELS)
    nunito = "".join("".join(p[2]) for p in PANELS)
    parts = []
    for i, (num, title, lines, name) in enumerate(PANELS):
        (lt, lb), (rt, rb) = cuts[i], cuts[i + 1]
        g = 6 if i < 2 else 0
        poly = f"{lt + (6 if i else 0)},{top} {rt - g},{top} {rb - g},{bot} {lb + (6 if i else 0)},{bot}"
        lit = i != 1  # orange, black, orange
        bg, fg, sub = (ORANGE, INK, INK) if lit else (INK, PAPER, PAPER)
        begin = 0.15 + i * 0.18
        x0 = max(lt, lb) + 24
        text = "".join(
            f'<text x="{x0}" y="{126 + j * 20}" font-family="\'Nunito\', system-ui, sans-serif" font-weight="800" font-size="14.5" fill="{sub}" fill-opacity="{0.85 if lit else 0.72}">{line.replace("&", "&amp;").replace("\'", "&#39;")}</text>'
            for j, line in enumerate(lines)
        )
        dots = halftone(rt - 60, top + 70, 140, 11, 3.6, INK if lit else ORANGE)
        parts.append(f"""
  <clipPath id="p{i}"><polygon points="{poly}"/></clipPath>
  <g opacity="0">
    <animate attributeName="opacity" values="0;1" dur="0.01s" begin="{begin:.2f}s" fill="freeze"/>
    <animateTransform attributeName="transform" type="translate" values="0 14;0 0" dur="0.45s" begin="{begin:.2f}s" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1" fill="freeze"/>
    <polygon points="{poly}" fill="{bg}"/>
    <g clip-path="url(#p{i})">
      <g opacity="{0.22 if lit else 0.5}">{dots}</g>
      <g>
        <animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0" dur="2.6s" begin="{i * 0.7:.1f}s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>
        <image href="{pose(name, 118)}" x="{rb - 128}" y="{bot - int(118 * POSE_RATIO[name]) - 6}" width="118" height="{int(118 * POSE_RATIO[name])}"/>
      </g>
    </g>
    <polygon points="{poly}" fill="none" stroke="{PAPER}" stroke-width="2.5" stroke-linejoin="round"/>
    <text x="{x0}" y="44" font-family="'Bangers', Impact, sans-serif" font-size="16" letter-spacing="2" fill="{fg}" fill-opacity="0.6">{num}</text>
    <text x="{x0}" y="92" font-family="'Bangers', Impact, sans-serif" font-size="48" letter-spacing="1.5" fill="{fg}">{title}</text>
    {text}
  </g>""")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Track: seven sources, one library. Airing: this season's schedule with reminders. Visit: scene map, trip planner and a shot-matching camera.">
  <title>What Aniseekr does</title>
  <!-- generated by scripts/render-cards.py — edit the script, not this file -->
  <defs>{fonts(bangers, nunito)}</defs>
  <rect x="8" y="8" width="{W - 8}" height="{H - 8}" fill="{ORANGE}"/>
  <rect x="1" y="1" width="{W - 10}" height="{H - 10}" fill="{CARD}" stroke="{PAPER}" stroke-width="2"/>{"".join(parts)}
</svg>
"""


OUT.mkdir(exist_ok=True)
for name, render in (("header", header), ("panels", panels)):
    svg = render()
    (OUT / f"{name}.svg").write_text(svg)
    print(f"{name}.svg {len(svg) / 1024:.0f} KB")
