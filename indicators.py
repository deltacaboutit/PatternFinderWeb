"""
indicators.py - Common technical indicators, written out with plain formulas.

Words used here:
  * Moving average (SMA): the average closing price over the last N periods.
    It smooths out day-to-day noise so the general direction is easier to see.
  * EMA (exponential moving average): like a moving average, but recent prices
    count a bit more than older ones, so it reacts faster.
  * RSI (Relative Strength Index): a number from 0 to 100 that compares the size
    of recent gains with recent losses. Above 70 is often called "overbought"
    (the price rose fast and may cool off). Below 30 is "oversold".
  * MACD: the gap between a fast EMA (12 periods) and a slow EMA (26 periods).
    Its "signal line" is a 9-period EMA of the MACD itself. When MACD crosses
    above the signal line, momentum is turning up; below means turning down.
  * ATR (Average True Range): the typical size of one period's price swing.
    The pattern finder uses it to decide what counts as a "meaningful" move.
"""

import numpy as np
import pandas as pd


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    change = close.diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)
    # Wilder's smoothing (the standard way RSI is calculated)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.fillna(100.0).where(avg_gain.notna())


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["Close"].shift(1)
    true_range = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / n, adjust=False).mean()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the price table with indicator columns added."""
    out = df.copy()
    c = out["Close"]
    out["SMA20"] = sma(c, 20)
    out["SMA50"] = sma(c, 50)
    out["SMA200"] = sma(c, 200)
    out["RSI"] = rsi(c)
    out["MACD"], out["MACD_signal"], out["MACD_hist"] = macd(c)
    out["ATR"] = atr(out)
    out["VolAvg20"] = sma(out["Volume"], 20)
    return out


def _bars_since_cross(a: pd.Series, b: pd.Series, lookback: int):
    """How many bars ago did line a cross line b? Returns (bars_ago, 'up'/'down') or None."""
    diff = (a - b).dropna()
    if len(diff) < 2:
        return None
    sign = np.sign(diff.values)
    for k in range(1, min(lookback, len(sign) - 1) + 1):
        now, before = sign[-k], sign[-k - 1]
        if now != before and now != 0:
            return k - 1, ("up" if now > 0 else "down")
    return None


def describe_indicators(df: pd.DataFrame, unit: str = "day") -> list:
    """Turn the latest indicator values into short plain-English sentences."""
    last = df.iloc[-1]
    price = last["Close"]
    notes = []

    # --- Trend from moving averages ---
    s50, s200 = last.get("SMA50"), last.get("SMA200")
    if pd.notna(s50) and pd.notna(s200):
        if price > s50 > s200:
            notes.append(
                f"Trend: UP. The price (${price:,.2f}) is above its 50-{unit} average "
                f"(${s50:,.2f}), and the 50-{unit} average is above the 200-{unit} average "
                f"(${s200:,.2f}). This is the classic picture of an uptrend."
            )
        elif price < s50 < s200:
            notes.append(
                f"Trend: DOWN. The price (${price:,.2f}) is below its 50-{unit} average "
                f"(${s50:,.2f}), which is below the 200-{unit} average (${s200:,.2f}). "
                "This is the classic picture of a downtrend."
            )
        else:
            notes.append(
                f"Trend: MIXED. The price (${price:,.2f}), the 50-{unit} average "
                f"(${s50:,.2f}) and the 200-{unit} average (${s200:,.2f}) are not lined up "
                "in one direction, so there is no clear long-term trend right now."
            )
        cross = _bars_since_cross(df["SMA50"], df["SMA200"], 20)
        if cross:
            ago, way = cross
            when = "on the latest bar" if ago == 0 else f"{ago} {unit}(s) ago"
            if way == "up":
                notes.append(
                    f"A 'golden cross' happened {when}: the 50-{unit} average moved above "
                    f"the 200-{unit} average. Many traders see this as a bullish (positive) sign."
                )
            else:
                notes.append(
                    f"A 'death cross' happened {when}: the 50-{unit} average moved below "
                    f"the 200-{unit} average. Many traders see this as a bearish (negative) sign."
                )
    elif pd.notna(s50):
        side = "above" if price > s50 else "below"
        notes.append(
            f"Trend: the price is {side} its 50-{unit} average (${s50:,.2f}). "
            f"There is not enough history for a 200-{unit} average; pick a longer period to see it."
        )

    # --- RSI ---
    r = last.get("RSI")
    if pd.notna(r):
        if r >= 70:
            notes.append(
                f"RSI is {r:.0f} (above 70): 'overbought'. The price has risen quickly and "
                "may pause or pull back, although strong trends can stay overbought for a while."
            )
        elif r <= 30:
            notes.append(
                f"RSI is {r:.0f} (below 30): 'oversold'. The price has fallen quickly and "
                "may bounce, although weak stocks can stay oversold for a while."
            )
        else:
            mood = "slightly positive" if r > 55 else "slightly negative" if r < 45 else "neutral"
            notes.append(f"RSI is {r:.0f}, which is in the normal range (30 to 70). Momentum looks {mood}.")

    # --- MACD ---
    m, s = last.get("MACD"), last.get("MACD_signal")
    if pd.notna(m) and pd.notna(s):
        cross = _bars_since_cross(df["MACD"], df["MACD_signal"], 5)
        if cross:
            ago, way = cross
            when = "on the latest bar" if ago == 0 else f"{ago} {unit}(s) ago"
            word = "above" if way == "up" else "below"
            tone = "turning up (bullish)" if way == "up" else "turning down (bearish)"
            notes.append(f"MACD crossed {word} its signal line {when}. Short-term momentum is {tone}.")
        elif m > s:
            notes.append("MACD is above its signal line, so short-term momentum is pointing up.")
        else:
            notes.append("MACD is below its signal line, so short-term momentum is pointing down.")

    # --- Volume ---
    v, va = last.get("Volume"), last.get("VolAvg20")
    if pd.notna(va) and va > 0 and v > 0:
        ratio = v / va
        if ratio >= 1.5:
            notes.append(
                f"Volume on the latest bar was {ratio:.1f} times the 20-{unit} average. "
                "Heavy volume means many traders were active, which gives the latest move more weight."
            )
        elif ratio <= 0.6:
            notes.append(f"Volume on the latest bar was light ({ratio:.1f} times the 20-{unit} average).")
    return notes
