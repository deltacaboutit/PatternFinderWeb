"""
make_pattern_pictures.py - Draws one example picture for each chart pattern.

The pictures are made by the app's own pattern finder: it builds a clean,
textbook price path for each pattern (the same ones used in the self-test),
finds the pattern on it, and draws what it found. So the pictures in the
Guide show exactly the lines, entry, target and stop-loss that the app uses.

Run it once after changing the pattern rules:
    python make_pattern_pictures.py
It saves PNG files in the folder images/patterns/.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tests"))
from test_patterns import CASES, bowl, flipped, make_chart, path  # noqa: E402
from pattern_info import PATTERN_INFO  # noqa: E402
from patterns import find_patterns  # noqa: E402

OUT_DIR = os.path.join(HERE, "images", "patterns")
GREEN, RED, PURPLE, BLUE = "#1a9850", "#d73027", "#7b3294", "#1f5fbf"
INK, MUTED = "#222222", "#777777"


# A few example shapes are extended so the picture also shows what happens
# after the breakout (the self-test versions stop earlier).
_WEDGE = [(0, 75), (12, 92), (20, 88), (32, 99), (40, 96), (52, 104.5), (58, 101), (66, 106.5),
          (71, 103.5), (80, 93), (88, 89)]
_BOWL = np.concatenate([path([(0, 120), (10, 112)]), bowl(101, 112, 80)[1:], path([(0, 112), (12, 117), (22, 126)])[1:]])
PICTURE_SHAPES = {
    "Rising Wedge": path(_WEDGE),
    "Falling Wedge": path(flipped(_WEDGE)),
    "Rounding Bottom": _BOWL,
    "Rounding Top": 200 - _BOWL,
}


def file_name(pattern_name: str) -> str:
    return pattern_name.lower().replace(" ", "_").replace("-", "_") + ".png"


def draw(name: str, path: str) -> None:
    closes = PICTURE_SHAPES.get(name, CASES[name])
    df = make_chart(closes, seed=sum(map(ord, name)), noise=0.0)
    found = [p for p in find_patterns(df, "Medium") if p.name == name]
    if not found:
        raise RuntimeError(f"The pattern finder did not find {name} in its own example")
    p = found[0]
    info = PATTERN_INFO[name]
    c = df["Close"].to_numpy()
    n = len(c)
    color = GREEN if p.direction > 0 else RED if p.direction < 0 else PURPLE
    if p.direction == 0:
        color = GREEN if p.breakout_i is not None and c[p.breakout_i] > c[p.end] else PURPLE

    fig, ax = plt.subplots(figsize=(4.6, 2.9), dpi=110)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.83, bottom=0.05)
    x = np.arange(n)
    ax.axvspan(p.start, p.end, color=color, alpha=0.08, linewidth=0)
    ax.plot(x, c, color=INK, linewidth=1.6, solid_capstyle="round", zorder=3)

    curve = p.details.get("cup_curve")
    if curve:
        a, b = curve
        t = np.linspace(0, 1, b - a + 1)
        ax.plot(np.arange(a, b + 1), np.polyval(np.polyfit(t, c[a:b + 1], 2), t),
                color=color, linewidth=2.4, alpha=0.6, zorder=2)
    for i1, p1, i2, p2 in p.lines:
        ax.plot([i1, i2], [p1, p2], color=color, linewidth=2.0, zorder=4)
    ext = p.breakout_i if p.breakout_i is not None else n - 1
    for sc in p.scenarios[:1] if p.breakout_i is not None else p.scenarios:
        i1 = sc.line[0]
        ax.plot([i1, ext], [sc.level(i1), sc.level(ext)], color=color, linewidth=1.2, linestyle="--", zorder=4)

    ymin, ymax = c.min(), c.max()
    span = ymax - ymin
    for i, price, label in p.points:
        ax.plot(i, price, "o", color=color, markersize=4.5, markeredgecolor="white", markeredgewidth=0.7, zorder=5)
        if label in ("Touch",):
            continue
        above = price >= np.median(c[max(0, i - 3):i + 4])
        ax.annotate(label, (i, price), xytext=(0, 7 if above else -11), textcoords="offset points",
                    ha="center", fontsize=7, color=color, fontweight="bold", zorder=6)

    if p.breakout_i is not None:
        b = p.breakout_i
        ax.plot(b, c[b], "^" if p.direction > 0 else "v", color=color, markersize=9,
                markeredgecolor="black", markeredgewidth=0.6, zorder=6)
        ax.annotate("Breakout", (b, c[b]), xytext=(6, -12 if p.direction > 0 else 8),
                    textcoords="offset points", fontsize=7, color=INK, zorder=6)

    # Entry, target and stop
    x0 = p.breakout_i if p.breakout_i is not None else p.end
    x1 = n - 1 + 2
    levels = [(p.target, GREEN, "Target", "--"), (p.stop, RED, "Stop-loss", "--"), (p.entry, BLUE, "Entry", ":")]
    for val, col, lab, style in levels:
        if np.isfinite(val):
            ax.hlines(val, x0, x1, colors=col, linestyles=style, linewidth=1.2, zorder=4)
            ax.text(x1 + 0.01 * n, val, lab, va="center", ha="left", fontsize=7, color=col, fontweight="bold")
            ymin, ymax = min(ymin, val), max(ymax, val)

    pad = (ymax - ymin) * 0.08
    ax.set_ylim(ymin - pad, ymax + pad * 1.6)
    ax.set_xlim(-2, n + 0.2 * n)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.axhline(ymin - pad, color="#dddddd", linewidth=0.8)

    bias_col = GREEN if info["bias"] == "Bullish" else RED if info["bias"] == "Bearish" else PURPLE
    fig.text(0.03, 0.93, name, fontsize=11, fontweight="bold", color=INK, va="center")
    fig.text(0.97, 0.93, f"{info['category']} · {info['bias']}", fontsize=8, color=bias_col,
             ha="right", va="center", fontweight="bold")
    fig.text(0.03, 0.865, "Example shape (not real prices)", fontsize=6.5, color=MUTED, va="center")
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in PATTERN_INFO:
        out = os.path.join(OUT_DIR, file_name(name))
        draw(name, out)
        print("saved", out)


if __name__ == "__main__":
    main()
