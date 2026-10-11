"""
report.py - Turns the numbers into plain-English text for the app.
"""

import numpy as np

from indicators import describe_indicators
from pattern_info import DISCLAIMER, PATTERN_INFO, STATUS_HELP
from patterns import (ACTIVE_STATUSES, STATUS_CONFIRMED, STATUS_EXPIRED, STATUS_FAILED,
                      STATUS_FORMING, STATUS_STOPPED, STATUS_TARGET, is_recent)


def money(x) -> str:
    if x is None or not np.isfinite(x):
        return "n/a"
    return f"${x:,.2f}"


def pct(a, b) -> str:
    """Percentage change from a to b, with a sign."""
    if not (np.isfinite(a) and np.isfinite(b)) or a == 0:
        return ""
    return f"{(b - a) / a * 100:+.1f}%"


def bias_word(p) -> str:
    if p.direction > 0:
        return "Bullish"
    if p.direction < 0:
        return "Bearish"
    return "Either way"


def date_str(df, i, unit="day") -> str:
    if i is None:
        return ""
    i = max(0, min(int(i), len(df) - 1))
    d = df.index[i]
    return d.strftime("%Y-%m-%d %H:%M") if unit == "hour" else d.strftime("%Y-%m-%d")


def key_date(p, df, unit="day") -> str:
    """The date shown in tables: breakout date if there was one, else the pattern end."""
    return date_str(df, p.breakout_i if p.breakout_i is not None else p.end, unit)


def pattern_text(p, df, unit="day") -> str:
    info = PATTERN_INFO.get(p.name, {})
    n = len(df)
    last_close = float(df["Close"].iloc[-1])
    lines = []
    lines.append(f"{p.name}")
    lines.append(f"{info.get('category', '')} pattern  |  usual direction: {info.get('bias', '')}")
    lines.append("")
    lines.append(f"Status: {p.status}")
    lines.append(STATUS_HELP.get(p.status, ""))
    lines.append("")
    lines.append(f"The shape formed between {date_str(df, p.start, unit)} and {date_str(df, p.end, unit)}.")
    if p.breakout_i is not None:
        way = "above" if p.direction > 0 else "below"
        lines.append(f"Price closed {way} the breakout line on {date_str(df, p.breakout_i, unit)}.")
    if p.outcome_i is not None:
        what = {STATUS_TARGET: "reached the target", STATUS_STOPPED: "hit the stop-loss",
                STATUS_FAILED: "moved through the stop-loss level"}.get(p.status, "")
        if what:
            lines.append(f"It {what} on {date_str(df, p.outcome_i, unit)}.")
    lines.append("")
    lines.append("WHAT IT LOOKS LIKE")
    lines.append(info.get("looks", ""))
    lines.append("")
    lines.append("WHAT IT MAY MEAN")
    lines.append(info.get("means", ""))
    lines.append("")

    two_sided = p.status in (STATUS_FORMING, STATUS_EXPIRED) and len(p.scenarios) > 1
    lines.append("THE NUMBERS")
    if two_sided:
        lines.append("This pattern can break either way, so here are both cases, using where the lines "
                     "are on the latest bar:")
        for sc in p.scenarios:
            lvl = sc.level(n - 1)
            tgt = sc.target_from(lvl)
            word = "UP" if sc.direction > 0 else "DOWN"
            cond = "above" if sc.direction > 0 else "below"
            rr = abs(tgt - lvl) / abs(lvl - sc.stop) if abs(lvl - sc.stop) > 0 else float("nan")
            lines.append(f"  If it breaks {word} (a close {cond} {money(lvl)}):")
            lines.append(f"     target {money(tgt)} ({pct(lvl, tgt)}),  stop-loss {money(sc.stop)} "
                         f"({pct(lvl, sc.stop)}),  reward-to-risk {rr:.1f} to 1")
    else:
        cond = "above" if p.direction > 0 else "below"
        lines.append(f"  Breakout level (entry): {money(p.entry)}")
        if p.status == STATUS_FORMING:
            lines.append(f"     A close {cond} this level would confirm the pattern. The line can be sloped, "
                         "so this level is where it sits on the latest bar.")
        lines.append(f"  Projected target: {money(p.target)}  ({pct(p.entry, p.target)} from the entry)")
        lines.append(f"     How it is worked out: {info.get('target', '')}")
        lines.append(f"  Stop-loss: {money(p.stop)}  ({pct(p.entry, p.stop)} from the entry)")
        lines.append(f"     Why there: {info.get('stop', '')}")
        rr = p.reward_risk
        if np.isfinite(rr):
            lines.append(f"  Reward-to-risk: {rr:.1f} to 1")
            if rr >= 2:
                lines.append("     The projected gain is at least twice the possible loss.")
            elif rr >= 1:
                lines.append("     The projected gain is a bit larger than the possible loss.")
            else:
                lines.append("     The possible loss is larger than the projected gain, so this setup "
                             "is less attractive on its own.")
    lines.append(f"  Quality score: {p.score:.0f} out of 100")
    lines.append("     This shows how closely the shape matches the textbook pattern. It is not the "
                 "chance that the trade will work.")
    if p.status in ACTIVE_STATUSES:
        lines.append("")
        lines.append(f"Latest close: {money(last_close)}.")
        if p.status == STATUS_CONFIRMED:
            lines.append(f"That is {pct(last_close, p.target)} away from the target and "
                         f"{pct(last_close, p.stop)} away from the stop-loss.")
        elif not two_sided:
            lines.append(f"That is {pct(last_close, p.entry)} away from the breakout level.")
    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def track_record(pats):
    done = [p for p in pats if p.status in (STATUS_TARGET, STATUS_STOPPED)]
    hits = sum(p.status == STATUS_TARGET for p in done)
    return len(done), hits


def summary_text(ticker, df, pats, unit="day") -> str:
    n = len(df)
    last = df.iloc[-1]
    lines = [f"{ticker}  -  summary", ""]
    adj = {"day": "daily ", "week": "weekly ", "hour": "hourly "}.get(unit, "")
    lines.append(f"{n} {adj}bars from {date_str(df, 0, unit)} to {date_str(df, n - 1, unit)}.")
    lines.append(f"Latest close: {money(float(last['Close']))}")
    lines.append("")
    lines.append("WHAT THE INDICATORS SAY")
    for s in describe_indicators(df, unit=unit if unit != "bar" else "bar"):
        lines.append(f"  - {s}")
    lines.append("")
    lines.append("PATTERNS")
    active = [p for p in pats if is_recent(p, n)]
    lines.append(f"Found {len(pats)} pattern(s) on this chart. {len(active)} of them are active right now "
                 "(still forming, or broke out within the last 10 bars).")
    for p in active[:8]:
        if p.status == STATUS_FORMING and len(p.scenarios) > 1:
            lines.append(f"  - {p.name} ({p.status}, could break either way)")
        else:
            lines.append(f"  - {p.name} ({bias_word(p)}, {p.status}): entry {money(p.entry)}, "
                         f"target {money(p.target)}, stop {money(p.stop)}")
    if not active:
        lines.append("  No pattern is forming or has just broken out right now.")
    total, hits = track_record(pats)
    if total:
        lines.append("")
        lines.append("TRACK RECORD ON THIS CHART")
        lines.append(f"Of the {total} earlier patterns that broke out and then reached either their "
                     f"target or their stop, {hits} reached the target first and {total - hits} hit the "
                     "stop first. A small sample like this is only a rough guide.")
    lines.append("")
    lines.append("Click a pattern in the list to see it on the chart with its entry, target and stop-loss.")
    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)
