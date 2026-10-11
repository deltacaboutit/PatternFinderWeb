"""
patterns.py - Finds chart patterns using mathematical rules.

How it works, step by step
--------------------------
1. Swing points ("pivots").
   A swing high is a peak: the price rose to it and then fell back by a
   meaningful amount. A swing low is the opposite. "Meaningful" is measured
   with the ATR (the typical size of one bar's move), so the same rules work
   for a $5 stock and a $500 stock. The sensitivity setting changes how big
   a move must be (Low = only big swings, High = smaller swings too).

2. Shape rules.
   Each pattern is a short list of conditions on those swing points, for
   example a Double Top is "peak, dip, peak, with both peaks at about the same
   price". Straight lines (trendlines) are fitted with linear regression,
   which finds the straight line closest to a set of points. Rounded shapes
   (cups and rounding bottoms) are fitted with a parabola (a U-shaped curve)
   and we check how well it fits using R-squared (1.0 = perfect fit).

3. Price levels.
   * Breakout level (entry): the line price must close beyond to confirm.
   * Target (projected move): the classic "measured move" - the height of the
     pattern added to (or subtracted from) the breakout level.
   * Stop-loss: the price that would prove the pattern wrong.

4. What happened next.
   The program then checks later bars to see whether the pattern is still
   forming, broke out, reached its target, or hit its stop.

Bearish versions of patterns are found by flipping the chart upside down
(price -> K - price) and running the bullish rules (or vice versa). That
keeps every rule perfectly symmetrical.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

# How many ATRs a swing must cover to count as a swing point.
SENSITIVITY = {"Low": 3.0, "Medium": 2.0, "High": 1.3}

STATUS_FORMING = "Forming"
STATUS_CONFIRMED = "Confirmed"
STATUS_TARGET = "Target reached"
STATUS_STOPPED = "Stopped out"
STATUS_FAILED = "Failed"
STATUS_EXPIRED = "Expired"
ACTIVE_STATUSES = (STATUS_FORMING, STATUS_CONFIRMED)

# A close must be this many ATRs beyond a line to count as a breakout,
# so that a close sitting right on the line is not mistaken for one.
BREAK_MARGIN = 0.1


# ----------------------------------------------------------------------------
# Small building blocks
# ----------------------------------------------------------------------------
@dataclass
class Pivot:
    i: int          # bar number
    p: float        # price
    t: str          # 'H' = swing high, 'L' = swing low
    tentative: bool = False  # True for the latest swing, which may still change


@dataclass
class Scenario:
    """One possible breakout. Most patterns have one; triangles/rectangles have two."""
    direction: int                 # +1 = price expected to go up, -1 = down
    line: tuple                    # breakout line (i1, p1, i2, p2)
    height: float                  # measured-move size
    stop: float                    # stop-loss price
    fixed_target: Optional[float] = None  # used instead of height when set (wedges)

    def level(self, i: int) -> float:
        return line_at(self.line, i)

    def target_from(self, level: float) -> float:
        if self.fixed_target is not None:
            return self.fixed_target
        return level + self.direction * self.height


@dataclass
class Pattern:
    name: str
    family: str
    start: int
    end: int
    points: list                    # [(bar, price, label), ...]
    lines: list                     # [(i1, p1, i2, p2), ...] lines to draw
    scenarios: List[Scenario]
    score: float
    details: dict = field(default_factory=dict)
    # Filled in by evaluate():
    status: str = ""
    direction: int = 0
    breakout_i: Optional[int] = None
    outcome_i: Optional[int] = None
    entry: float = float("nan")
    target: float = float("nan")
    stop: float = float("nan")

    @property
    def reward_risk(self) -> float:
        risk = abs(self.entry - self.stop)
        if not np.isfinite(risk) or risk <= 0:
            return float("nan")
        return abs(self.target - self.entry) / risk

    @property
    def last_bar(self) -> int:
        """Last bar that belongs to the pattern story (end, breakout or outcome)."""
        return max(x for x in (self.end, self.breakout_i, self.outcome_i) if x is not None)


def line_at(line: tuple, i: float) -> float:
    i1, p1, i2, p2 = line
    if i2 == i1:
        return p1
    return p1 + (p2 - p1) * (i - i1) / (i2 - i1)


def _fit_line(xs, ys):
    """Least-squares straight line. Returns (slope, intercept)."""
    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)
    if len(xs) < 2 or np.ptp(xs) == 0:
        return 0.0, float(np.mean(ys))
    slope, intercept = np.polyfit(xs, ys, 1)
    return float(slope), float(intercept)


def _parabola_fit(y):
    """Fit y = a*x^2 + b*x + c with x scaled to 0..1. Returns (a, vertex_x, r_squared)."""
    y = np.asarray(y, float)
    x = np.linspace(0.0, 1.0, len(y))
    a, b, c = np.polyfit(x, y, 2)
    fitted = a * x * x + b * x + c
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2)) or 1e-12
    vertex = -b / (2 * a) if a != 0 else 0.5
    return float(a), float(vertex), 1.0 - ss_res / ss_tot


def _hull_line(x, y, upper: bool, tol: float):
    """A trendline that touches the most extreme point and sits on one side of all points.

    For a lower line every point is on or above it; for an upper line every
    point is on or below it. Of the two possible lines (pivoting to the left or
    to the right of the extreme point) we keep the one touching more points.
    Returns (slope, intercept).
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    yy = -y if upper else y
    m = int(np.argmin(yy))
    after, before = x > x[m], x < x[m]
    options = []
    if after.any():
        options.append(float(np.min((yy[after] - yy[m]) / (x[after] - x[m]))))
    if before.any():
        options.append(float(np.max((yy[before] - yy[m]) / (x[before] - x[m]))))
    if not options:
        options = [0.0]
    best, best_touch = options[0], -1
    for s in options:
        line = yy[m] + s * (x - x[m])
        touch = _touch_groups(x[(yy - line) <= tol].astype(int))
        if touch > best_touch:
            best, best_touch = s, touch
    slope = -best if upper else best
    return slope, float(y[m] - slope * x[m])


def _touch_groups(bars_touching) -> int:
    """Count separate visits to a line (touches at least 3 bars apart count as new visits)."""
    groups, last = 0, None
    for i in bars_touching:
        if last is None or i - last >= 3:
            groups += 1
        last = i
    return groups


def _clip01(x):
    return float(min(1.0, max(0.0, x)))


class Bars:
    """Price arrays plus helpers. Can be flipped upside down for bearish searches."""

    def __init__(self, o, h, l, c, v, atr, ref, K=None):
        self.o, self.h, self.l, self.c, self.v = o, h, l, c, v
        self.atr = atr
        self.ref = ref                  # real closing price, used for percentages
        self.n = len(c)
        self.K = K                      # None = normal chart, number = flipped chart
        # "About the same price" tolerance: one ATR, kept between 1.5% and 4% of price
        self.tol = np.clip(atr, 0.015 * ref, 0.04 * ref)

    @classmethod
    def from_df(cls, df: pd.DataFrame):
        o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
        v = df["Volume"].to_numpy(float)
        prev = np.concatenate([[c[0]], c[:-1]])
        tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
        atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
        atr = np.maximum(atr, 1e-9)
        return cls(o, h, l, c, v, atr, c.copy())

    def mirror(self):
        K = float(np.max(self.h) + np.min(self.l))
        return Bars(K - self.o, K - self.l, K - self.h, K - self.c, self.v, self.atr, self.ref, K=K)

    def buf(self, i):
        """Small safety gap added beyond stop-loss levels (a quarter of an ATR)."""
        return 0.25 * self.atr[min(i, self.n - 1)]


# ----------------------------------------------------------------------------
# Step 1: swing points (a "zigzag")
# ----------------------------------------------------------------------------
def find_pivots(b: Bars, atr_mult: float) -> List[Pivot]:
    h, l, n = b.h, b.l, b.n
    if n < 3:
        return []
    th = np.maximum(atr_mult * b.atr, 0.01 * b.ref)
    piv: List[Pivot] = []
    trend = 0
    hi_i = lo_i = 0
    ext = 0
    for i in range(1, n):
        if trend == 0:
            if h[i] > h[hi_i]:
                hi_i = i
            if l[i] < l[lo_i]:
                lo_i = i
            if hi_i != lo_i and h[hi_i] - l[lo_i] >= th[i]:
                if hi_i > lo_i:
                    piv.append(Pivot(lo_i, l[lo_i], "L"))
                    trend, ext = 1, hi_i
                else:
                    piv.append(Pivot(hi_i, h[hi_i], "H"))
                    trend, ext = -1, lo_i
        elif trend == 1:  # rising, waiting for a peak
            if h[i] >= h[ext]:
                ext = i
            elif h[ext] - l[i] >= th[ext]:
                piv.append(Pivot(ext, h[ext], "H"))
                seg = l[ext + 1:i + 1]
                ext = ext + 1 + int(np.argmin(seg))
                trend = -1
        else:  # falling, waiting for a trough
            if l[i] <= l[ext]:
                ext = i
            elif h[i] - l[ext] >= th[ext]:
                piv.append(Pivot(ext, l[ext], "L"))
                seg = h[ext + 1:i + 1]
                ext = ext + 1 + int(np.argmax(seg))
                trend = 1
    if trend == 1:
        piv.append(Pivot(ext, h[ext], "H", tentative=True))
    elif trend == -1:
        piv.append(Pivot(ext, l[ext], "L", tentative=True))
    return piv


def mirror_pivots(piv: List[Pivot], K: float) -> List[Pivot]:
    return [Pivot(p.i, K - p.p, "L" if p.t == "H" else "H", p.tentative) for p in piv]


def mirror_pattern(p: Pattern, K: float, name: str, family: str) -> Pattern:
    """Flip a pattern found on the upside-down chart back to the real chart."""
    f = lambda x: K - x
    ml = lambda ln: (ln[0], f(ln[1]), ln[2], f(ln[3]))
    return Pattern(
        name=name,
        family=family,
        start=p.start,
        end=p.end,
        points=[(i, f(pr), lab) for i, pr, lab in p.points],
        lines=[ml(ln) for ln in p.lines],
        scenarios=[
            Scenario(
                direction=-s.direction,
                line=ml(s.line),
                height=s.height,
                stop=f(s.stop),
                fixed_target=None if s.fixed_target is None else f(s.fixed_target),
            )
            for s in p.scenarios
        ],
        score=p.score,
        details=dict(p.details),
    )


def _prior_trend_up(b: Bars, piv, k, ref_price) -> float:
    """1.0 if price came from below ref_price before pivot k, else 0.0 (for tops)."""
    if k - 1 >= 0:
        return 1.0 if piv[k - 1].p < ref_price else 0.0
    start = max(0, piv[k].i - 20)
    return 1.0 if b.l[start:piv[k].i + 1].min() < ref_price else 0.0


# ----------------------------------------------------------------------------
# Double top, triple top, head and shoulders  (bottoms = flipped chart)
# ----------------------------------------------------------------------------
def detect_tops(b: Bars, piv: List[Pivot], names: dict, peak="Peak", trough="Dip") -> List[Pattern]:
    out = []
    np_ = len(piv)
    fam = names["family"]
    for k in range(np_):
        if piv[k].t != "H":
            continue

        # ---------- Double top: peak, dip, peak ----------
        if k + 2 < np_:
            h1, lo, h2 = piv[k], piv[k + 1], piv[k + 2]
            tol = b.tol[h2.i]
            top = max(h1.p, h2.p)
            mean = (h1.p + h2.p) / 2
            depth = mean - lo.p
            if (
                abs(h1.p - h2.p) <= tol
                and h2.i - h1.i >= 5
                and depth >= max(2 * tol, 0.03 * b.ref[lo.i])
                and _prior_trend_up(b, piv, k, lo.p)
            ):
                v1 = b.v[max(0, h1.i - 2):h1.i + 3].mean()
                v2 = b.v[max(0, h2.i - 2):h2.i + 3].mean()
                score = (
                    40 * (1 - abs(h1.p - h2.p) / tol)
                    + 30 * _clip01(depth / (4 * tol))
                    + 15
                    + (15 if v1 > 0 and v2 < v1 else 0)
                )
                neck = (lo.i, lo.p, h2.i, lo.p)
                out.append(Pattern(
                    names["double"], fam, h1.i, h2.i,
                    points=[(h1.i, h1.p, f"{peak} 1"), (lo.i, lo.p, trough), (h2.i, h2.p, f"{peak} 2")],
                    lines=[(h1.i, lo.p, h2.i, lo.p)],
                    scenarios=[Scenario(-1, neck, depth, top + b.buf(h2.i))],
                    score=score, details={"height": depth},
                ))

        # ---------- Triple top and head & shoulders: 5 swing points ----------
        if k + 4 < np_:
            h1, l1, h2, l2, h3 = piv[k:k + 5]
            tol = b.tol[h3.i]
            highs = np.array([h1.p, h2.p, h3.p])
            neck_low = min(l1.p, l2.p)
            if not _prior_trend_up(b, piv, k, neck_low):
                continue

            # Triple top: three peaks at about the same price
            if highs.max() - highs.min() <= 1.5 * tol:
                depth = highs.mean() - neck_low
                if depth >= max(2 * tol, 0.03 * b.ref[l1.i]):
                    score = 45 * (1 - (highs.max() - highs.min()) / (1.5 * tol)) + 30 * _clip01(depth / (4 * tol)) + 25
                    neck = (l1.i, neck_low, h3.i, neck_low)
                    out.append(Pattern(
                        names["triple"], fam, h1.i, h3.i,
                        points=[(h1.i, h1.p, f"{peak} 1"), (l1.i, l1.p, trough), (h2.i, h2.p, f"{peak} 2"),
                                (l2.i, l2.p, trough), (h3.i, h3.p, f"{peak} 3")],
                        lines=[(h1.i, neck_low, h3.i, neck_low)],
                        scenarios=[Scenario(-1, neck, depth, highs.max() + b.buf(h3.i))],
                        score=score, details={"height": depth},
                    ))

            # Head and shoulders: middle peak clearly highest
            ls, head, rs = h1, h2, h3
            neck = (l1.i, l1.p, l2.i, l2.p)
            neck_at_head = line_at(neck, head.i)
            height = head.p - neck_at_head
            t1, t2 = head.i - ls.i, rs.i - head.i
            if (
                height > 0
                and head.p - max(ls.p, rs.p) >= 0.5 * tol
                and abs(ls.p - rs.p) <= max(1.5 * tol, 0.35 * height)
                and abs(l1.p - l2.p) <= 0.6 * height
                and 1 / 3 <= t1 / max(t2, 1) <= 3
                and height >= max(2 * tol, 0.03 * b.ref[head.i])
                and min(ls.p, rs.p) > max(l1.p, l2.p)
            ):
                score = (
                    30 * (1 - abs(ls.p - rs.p) / max(1.5 * tol, 0.35 * height))
                    + 20 * (1 - abs(np.log(t1 / max(t2, 1))) / np.log(3))
                    + 20 * (1 - abs(l1.p - l2.p) / (0.6 * height))
                    + 15 * _clip01((head.p - max(ls.p, rs.p)) / (2 * tol))
                    + 15
                )
                out.append(Pattern(
                    names["hs"], fam, ls.i, rs.i,
                    points=[(ls.i, ls.p, "Left shoulder"), (l1.i, l1.p, "Neckline"), (head.i, head.p, "Head"),
                            (l2.i, l2.p, "Neckline"), (rs.i, rs.p, "Right shoulder")],
                    lines=[neck],
                    scenarios=[Scenario(-1, neck, height, rs.p + b.buf(rs.i))],
                    score=score, details={"height": height},
                ))
    return out


# ----------------------------------------------------------------------------
# Triangles, wedges and rectangles (lines through swing highs and swing lows)
# ----------------------------------------------------------------------------
def detect_ranges(b: Bars, piv: List[Pivot], kinds: dict) -> List[Pattern]:
    """kinds maps 'rect' / 'asc' / 'sym' / 'wedge' to the pattern name to use."""
    out = []
    for s in range(len(piv)):
        for m in range(5, 9):
            e = s + m - 1
            if e >= len(piv):
                break
            seg = piv[s:e + 1]
            highs = [p for p in seg if p.t == "H"]
            lows = [p for p in seg if p.t == "L"]
            if len(highs) < 2 or len(lows) < 2:
                continue
            i0, i1 = seg[0].i, seg[-1].i
            w = i1 - i0
            if w < 10:
                continue
            su, iu = _fit_line([p.i for p in highs], [p.p for p in highs])
            sl, il = _fit_line([p.i for p in lows], [p.p for p in lows])
            up = lambda i: su * i + iu
            lo = lambda i: sl * i + il
            h0, h1 = up(i0) - lo(i0), up(i1) - lo(i1)
            if h0 <= 0 or h1 <= 0:
                continue
            # Real height of the swings (lines extended backwards can exaggerate it)
            H_real = max(p.p for p in highs) - min(p.p for p in lows)
            H = min(max(h0, h1), H_real)
            if H < 2 * b.tol[i1]:
                continue
            du, dl = su * w, sl * w
            fit_err = max(
                max(abs(p.p - up(p.i)) for p in highs),
                max(abs(p.p - lo(p.i)) for p in lows),
            ) / H
            if fit_err > 0.2:
                continue
            idx = np.arange(i0, i1 + 1)
            outside = np.mean(
                (b.c[idx] > up(idx) + 0.25 * b.atr[idx]) | (b.c[idx] < lo(idx) - 0.25 * b.atr[idx])
            )
            if outside > 0.1:
                continue

            flat_u, flat_l = abs(du) <= 0.2 * H, abs(dl) <= 0.2 * H
            kind = None
            if flat_u and flat_l and h1 >= 0.7 * h0 and h1 <= 1.4 * h0:
                kind = "rect"
            elif flat_u and dl >= 0.3 * H and h1 < 0.75 * h0:
                kind = "asc"
            elif du <= -0.2 * H and dl >= 0.2 * H and h1 < 0.75 * h0:
                kind = "sym"
            elif du >= 0.2 * H and dl > du and (dl - du) >= 0.25 * h0:
                kind = "wedge"
            if kind not in kinds:
                continue

            upper = (i0, up(i0), i1, up(i1))
            lower = (i0, lo(i0), i1, lo(i1))
            score = (
                40 * (1 - fit_err / 0.2)
                + min(30, (len(seg) - 4) * 10)
                + 15 * _clip01(w / 30)
                + 15 * (1 - outside / 0.1)
            )
            # Which way was price heading before the pattern? (used for two-sided patterns)
            before = max(0, i0 - max(w, 20))
            came_up = b.c[i0] >= b.c[before]

            # Stops go just beyond the most recent swing on the opposite side
            last_low = lows[-1].p - b.buf(i1)
            last_high = highs[-1].p + b.buf(i1)
            if kind == "rect":
                mid = (up(i1) + lo(i1)) / 2
                hh = min((h0 + h1) / 2, H)
                sc_up = Scenario(+1, upper, hh, mid)
                sc_dn = Scenario(-1, lower, hh, mid)
                scen = [sc_up, sc_dn] if came_up else [sc_dn, sc_up]
            elif kind == "asc":
                scen = [Scenario(+1, upper, H, last_low)]
            elif kind == "sym":
                sc_up = Scenario(+1, upper, H, last_low)
                sc_dn = Scenario(-1, lower, H, last_high)
                scen = [sc_up, sc_dn] if came_up else [sc_dn, sc_up]
            else:  # rising wedge: expected to break down, target = where the wedge began
                scen = [Scenario(-1, lower, H, last_high, fixed_target=lo(i0))]

            out.append(Pattern(
                kinds[kind], "range", i0, i1,
                points=[(p.i, p.p, "Touch") for p in seg],
                lines=[upper, lower],
                scenarios=scen,
                score=score,
                details={"height": H, "prior_up": bool(came_up)},
            ))
    return out


# ----------------------------------------------------------------------------
# Flags and pennants (sharp move = "pole", then a small pause)
# ----------------------------------------------------------------------------
def detect_flags(b: Bars, piv: List[Pivot], flag_name: str, pennant_name: str, family: str) -> List[Pattern]:
    out = []
    n = b.n
    for k in range(1, len(piv)):
        prev, hp = piv[k - 1], piv[k]
        if not (prev.t == "L" and hp.t == "H"):
            continue
        # The pole starts where the sharpest climb into the peak began
        # (a slow drift up before the sharp move is not part of the pole).
        s0 = max(prev.i, hp.i - 20)
        if s0 >= hp.i - 1:
            continue
        cand = np.arange(s0, hp.i - 1)
        steep = (hp.p - b.l[cand]) / np.sqrt(hp.i - cand)   # big move in few bars wins
        ps = int(cand[np.argmax(steep)])
        lp = Pivot(ps, b.l[ps], "L")
        pole = hp.p - lp.p
        bars_pole = hp.i - lp.i
        a = b.atr[hp.i]
        if not (2 <= bars_pole <= 25):
            continue
        if pole < max(3 * a, 0.05 * b.ref[hp.i]) or pole / bars_pole < 0.4 * a:
            continue

        max_len = min(25, max(8, 2 * bars_pole))
        found = None
        for e in range(hp.i + 4, min(hp.i + max_len, n - 1) + 1):
            idx = np.arange(hp.i, e + 1)
            retr = (hp.p - b.l[idx].min()) / pole
            if retr > 0.5:
                found = None
                break
            # Trendlines drawn the way a chartist would: resting on the highs / lows
            touch_tol = 0.3 * float(np.mean(b.atr[idx]))
            su, iu = _hull_line(idx, b.h[idx], upper=True, tol=touch_tol)
            sl, il = _hull_line(idx, b.l[idx], upper=False, tol=touch_tol)
            up = lambda i, su=su, iu=iu: su * i + iu
            lo = lambda i, sl=sl, il=il: sl * i + il
            L = e - hp.i
            h0, h1 = up(hp.i) - lo(hp.i), up(e) - lo(e)
            du, dl = su * L, sl * L
            if h0 <= 0 or h0 > 0.6 * pole:
                continue
            kind = None
            if du < 0 and dl > 0 and h1 < 0.7 * h0:
                kind = "pennant"
            elif du <= 0.05 * pole and dl <= 0.05 * pole and min(du, dl) < 0 and abs(du - dl) <= 0.8 * h0:
                kind = "flag"
            if kind is None:
                continue
            # The pause must bounce between its two lines at least twice each,
            # otherwise it is just the first few bars of a pullback.
            near_up = idx[b.h[idx] >= up(idx) - 0.2 * h0]
            near_lo = idx[b.l[idx] <= lo(idx) + 0.2 * h0]
            if _touch_groups(near_up) < 2 or _touch_groups(near_lo) < 2:
                continue
            found = (e, kind, (hp.i, up(hp.i), e, up(e)), (hp.i, lo(hp.i), e, lo(e)), retr, h0)
            if e + 1 <= n - 1 and b.c[e + 1] > up(e + 1) + BREAK_MARGIN * b.atr[e + 1]:
                break  # breakout on the next bar
            if e == n - 1:
                break  # still forming at the latest bar
        # If the pause ran out of room without a breakout we keep the last valid
        # shape; evaluate() will later mark it as broken out, failed or expired.
        if found is None:
            continue
        e, kind, upper, lower, retr, h0 = found
        idx = np.arange(hp.i, e + 1)
        flag_low = b.l[idx].min()
        v_pole = b.v[lp.i:hp.i + 1].mean()
        v_flag = b.v[hp.i + 1:e + 1].mean() if e > hp.i else v_pole
        score = (
            30 * _clip01(pole / (6 * a))
            + 25 * (1 - retr / 0.5)
            + 25 * _clip01(1 - h0 / (0.6 * pole))
            + (20 if v_pole > 0 and v_flag < v_pole else 0)
        )
        name = pennant_name if kind == "pennant" else flag_name
        out.append(Pattern(
            name, family, lp.i, e,
            points=[(lp.i, lp.p, "Pole start"), (hp.i, hp.p, "Pole top")],
            lines=[(lp.i, lp.p, hp.i, hp.p), upper, lower],
            scenarios=[Scenario(+1, upper, pole, flag_low - b.buf(e))],
            score=score, details={"height": pole, "pole_bars": bars_pole},
        ))
    return out


# ----------------------------------------------------------------------------
# Cup and handle (bullish only)
# ----------------------------------------------------------------------------
def detect_cup_handle(b: Bars, piv: List[Pivot]) -> List[Pattern]:
    out = []
    n = b.n
    highs = [p for p in piv if p.t == "H"]
    for a_i in range(len(highs)):
        L = highs[a_i]
        for c_i in range(a_i + 1, len(highs)):
            R = highs[c_i]
            w = R.i - L.i
            if w < 20:
                continue
            if w > 350:
                break
            rim = min(L.p, R.p)
            if abs(R.p - L.p) > max(0.05 * b.ref[R.i], 1.5 * b.tol[R.i]):
                continue
            inside_h = b.h[L.i + 1:R.i]
            if inside_h.size == 0 or inside_h.max() > rim + 0.25 * b.atr[R.i]:
                if inside_h.size and inside_h.max() > max(L.p, R.p) + 0.25 * b.atr[R.i]:
                    break  # a higher high inside: wider cups from L will fail too
                continue
            seg_l = b.l[L.i:R.i + 1]
            bot_i = L.i + int(np.argmin(seg_l))
            depth = rim - b.l[bot_i]
            dpct = depth / b.ref[bot_i]
            if not (0.08 <= dpct <= 0.5):
                continue
            pos = (bot_i - L.i) / w
            if not (0.2 <= pos <= 0.8):
                continue
            closes = b.c[L.i:R.i + 1]
            a2, vx, r2 = _parabola_fit(closes)
            if a2 <= 0 or r2 < 0.6:
                continue
            bottom_frac = float(np.mean(closes <= b.l[bot_i] + 0.4 * depth))
            if bottom_frac < 0.3:
                continue  # too "V" shaped: a cup should spend time near its bottom

            # Handle: a small dip after the right rim, then a close above the rim
            max_handle = min(40, max(5, int(0.5 * w)))
            handle_low = np.inf
            breakout = None
            ok = True
            for k in range(R.i + 1, min(n, R.i + max_handle + 1)):
                if b.c[k] > R.p and k - R.i >= 4:
                    breakout = k
                    break
                if b.c[k] > R.p:  # broke out before a handle formed - not this pattern
                    ok = False
                    break
                handle_low = min(handle_low, b.l[k])
                if R.p - handle_low > 0.5 * depth:
                    ok = False
                    break
            if not ok or not np.isfinite(handle_low):
                continue
            if breakout is None:
                last_k = min(n - 1, R.i + max_handle)
                if last_k != n - 1 or n - 1 - R.i < 3:
                    continue  # handle ran too long, or too short to judge yet
                end = n - 1
            else:
                end = breakout - 1
            handle_drop = (R.p - handle_low) / depth
            score = (
                30 * _clip01((r2 - 0.6) / 0.35)
                + 25 * (1 - abs(R.p - L.p) / max(0.05 * b.ref[R.i], 1.5 * b.tol[R.i]))
                + 25 * (1.0 if handle_drop <= 1 / 3 else _clip01((0.5 - handle_drop) / (0.5 - 1 / 3)))
                + 20 * _clip01((bottom_frac - 0.3) / 0.3)
            )
            line = (R.i, R.p, end, R.p)
            out.append(Pattern(
                "Cup and Handle", "bowl_bull", L.i, end,
                points=[(L.i, L.p, "Left rim"), (bot_i, b.l[bot_i], "Cup bottom"), (R.i, R.p, "Right rim"),
                        (int(R.i + 1 + np.argmin(b.l[R.i + 1:end + 1])), handle_low, "Handle low")],
                lines=[(L.i, R.p, end, R.p)],
                scenarios=[Scenario(+1, line, depth, handle_low - b.buf(end))],
                score=score, details={"height": depth, "r2": r2, "cup_curve": (L.i, R.i)},
            ))
    return out


# ----------------------------------------------------------------------------
# Rounding bottom (and rounding top on the flipped chart)
# ----------------------------------------------------------------------------
def detect_rounding(b: Bars, piv: List[Pivot], name: str, family: str) -> List[Pattern]:
    out = []
    n = b.n
    ends_all = sorted(set([p.i for p in piv] + [n - 1]))
    for Lp in [p for p in piv if p.t == "H"]:
        lip = Lp.p
        for end in ends_all:
            w = end - Lp.i
            if w < 40:
                continue
            if w > 400:
                break
            if b.h[Lp.i + 1:end + 1].max() > lip + 0.5 * b.atr[Lp.i]:
                break  # price went above the lip: no bowl from this starting point
            seg_l = b.l[Lp.i:end + 1]
            bot_i = Lp.i + int(np.argmin(seg_l))
            depth = lip - b.l[bot_i]
            if depth / b.ref[bot_i] < 0.10:
                continue
            pos = (bot_i - Lp.i) / w
            if not (0.3 <= pos <= 0.7):
                continue
            if b.c[end] - b.l[bot_i] < 0.5 * depth:
                continue
            closes = b.c[Lp.i:end + 1]
            a2, vx, r2 = _parabola_fit(closes)
            if a2 <= 0 or r2 < 0.75:
                continue
            bottom_frac = float(np.mean(closes <= b.l[bot_i] + 0.4 * depth))
            if bottom_frac < 0.3:
                continue
            tail = max(5, w // 5)
            stop = b.l[end - tail + 1:end + 1].min() - b.buf(end)
            score = 60 * _clip01((r2 - 0.75) / 0.2) + 20 * (1 - abs(pos - 0.5) / 0.2) + 20 * _clip01(depth / b.ref[bot_i] / 0.25)
            line = (Lp.i, lip, end, lip)
            out.append(Pattern(
                name, family, Lp.i, end,
                points=[(Lp.i, lip, "Lip"), (bot_i, b.l[bot_i], "Bottom of bowl")],
                lines=[line],
                scenarios=[Scenario(+1, line, depth, stop)],
                score=score, details={"height": depth, "r2": r2, "cup_curve": (Lp.i, end)},
            ))
    return out


# ----------------------------------------------------------------------------
# Step 4: what happened after the pattern?
# ----------------------------------------------------------------------------
def evaluate(p: Pattern, df_c, df_h, df_l, n: int, atr=None):
    width = max(1, p.end - p.start)
    max_wait = max(10, min(60, width))
    deadline = p.end + max_wait
    breakout = None
    for i in range(p.end + 1, n):
        if i > deadline:
            break
        for sc in p.scenarios:
            lv = sc.level(i)
            gap = BREAK_MARGIN * atr[i] if atr is not None else 0.0
            if (sc.direction > 0 and df_c[i] > lv + gap) or (sc.direction < 0 and df_c[i] < lv - gap):
                breakout = (i, sc)
                break
        if breakout:
            break
        if len(p.scenarios) == 1:
            sc = p.scenarios[0]
            if (sc.direction > 0 and df_c[i] < sc.stop) or (sc.direction < 0 and df_c[i] > sc.stop):
                p.status, p.direction, p.outcome_i = STATUS_FAILED, sc.direction, i
                p.entry = sc.level(i)
                p.target, p.stop = sc.target_from(p.entry), sc.stop
                return p

    if breakout is None:
        sc = p.scenarios[0]
        p.direction = sc.direction if len(p.scenarios) == 1 else 0
        p.status = STATUS_EXPIRED if n - 1 > deadline else STATUS_FORMING
        ref_i = min(n - 1, deadline) if p.status == STATUS_EXPIRED else n - 1
        p.entry = sc.level(max(ref_i, p.end))
        p.target, p.stop = sc.target_from(p.entry), sc.stop
        return p

    i_b, sc = breakout
    p.breakout_i, p.direction = i_b, sc.direction
    p.entry = sc.level(i_b)
    p.target, p.stop = sc.target_from(p.entry), sc.stop
    p.status = STATUS_CONFIRMED
    for j in range(i_b + 1, n):
        if sc.direction > 0:
            hit_stop, hit_tgt = df_l[j] <= p.stop, df_h[j] >= p.target
        else:
            hit_stop, hit_tgt = df_h[j] >= p.stop, df_l[j] <= p.target
        if hit_stop:  # if both happen on one bar we assume the worse case
            p.status, p.outcome_i = STATUS_STOPPED, j
            break
        if hit_tgt:
            p.status, p.outcome_i = STATUS_TARGET, j
            break
    return p


# ----------------------------------------------------------------------------
# Removing near-duplicates
# ----------------------------------------------------------------------------
PRIORITY = {
    "Head and Shoulders": 3, "Inverse Head and Shoulders": 3,
    "Triple Top": 2, "Triple Bottom": 2, "Cup and Handle": 2,
}


def _overlap(a: Pattern, b: Pattern) -> float:
    inter = min(a.end, b.end) - max(a.start, b.start)
    if inter <= 0:
        return 0.0
    return inter / max(1, min(a.end - a.start, b.end - b.start))


def dedupe(pats: List[Pattern]) -> List[Pattern]:
    order = sorted(pats, key=lambda p: (PRIORITY.get(p.name, 1), p.score), reverse=True)
    keep: List[Pattern] = []
    for p in order:
        if any(k.family == p.family and _overlap(k, p) > 0.5 for k in keep):
            continue
        keep.append(p)
    return keep


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------
def find_patterns(df: pd.DataFrame, sensitivity: str = "Medium") -> List[Pattern]:
    """Find every pattern in the price table. Newest patterns come first."""
    if len(df) < 30:
        return []
    b = Bars.from_df(df)
    piv = find_pivots(b, SENSITIVITY.get(sensitivity, 2.0))
    m = b.mirror()
    pivm = mirror_pivots(piv, m.K)
    flip = lambda pats, name_map, fam: [mirror_pattern(p, m.K, name_map.get(p.name, p.name), fam) for p in pats]

    pats: List[Pattern] = []
    pats += detect_tops(b, piv, {"double": "Double Top", "triple": "Triple Top",
                                 "hs": "Head and Shoulders", "family": "top"}, peak="Peak", trough="Dip")
    pats += flip(detect_tops(m, pivm, {"double": "Double Bottom", "triple": "Triple Bottom",
                                       "hs": "Inverse Head and Shoulders", "family": "bottom"},
                             peak="Trough", trough="Bounce"), {}, "bottom")
    pats += detect_flags(b, piv, "Bull Flag", "Bull Pennant", "flag_bull")
    pats += flip(detect_flags(m, pivm, "Bear Flag", "Bear Pennant", "flag_bear"), {}, "flag_bear")
    pats += detect_ranges(b, piv, {"rect": "Rectangle", "asc": "Ascending Triangle",
                                   "sym": "Symmetrical Triangle", "wedge": "Rising Wedge"})
    pats += flip(detect_ranges(m, pivm, {"asc": "Descending Triangle", "wedge": "Falling Wedge"}), {}, "range")
    pats += detect_cup_handle(b, piv)
    pats += detect_rounding(b, piv, "Rounding Bottom", "bowl_bull")
    pats += flip(detect_rounding(m, pivm, "Rounding Top", "bowl_bear"), {}, "bowl_bear")

    for p in pats:
        p.score = round(float(min(100, max(0, p.score))))
    pats = dedupe(pats)

    c, h, l = b.c, b.h, b.l
    for p in pats:
        evaluate(p, c, h, l, b.n, b.atr)
        # Fix point labels that were written for the flipped chart
        if p.name in ("Bear Flag", "Bear Pennant"):
            p.points = [(i, pr, lab.replace("top", "bottom")) for i, pr, lab in p.points]
        if p.name == "Rounding Top":
            p.points = [(i, pr, "Top of dome" if lab == "Bottom of bowl" else lab) for i, pr, lab in p.points]
    pats.sort(key=lambda p: (p.last_bar, p.end), reverse=True)
    return pats


def is_recent(p: Pattern, n: int, bars: int = 10) -> bool:
    """True if a pattern is still forming or broke out within the last few bars."""
    if p.status == STATUS_FORMING:
        return True
    if p.status == STATUS_CONFIRMED and p.breakout_i is not None:
        return p.breakout_i >= n - bars
    return False
