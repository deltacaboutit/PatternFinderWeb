"""
pattern_info.py - Plain-English descriptions shown inside the app.

Each pattern has:
  category - Reversal (trend may turn around), Continuation (trend may carry on)
             or Bilateral (could break either way)
  bias     - Bullish (expects price to rise), Bearish (expects a fall) or Neutral
  looks    - what the shape looks like on a chart
  means    - what traders usually take it to mean
  target   - how the projected move (price target) is worked out
  stop     - where the stop-loss is placed and why
"""

PATTERN_INFO = {
    # ---------------- Reversal patterns ----------------
    "Head and Shoulders": dict(
        category="Reversal", bias="Bearish",
        looks="Three peaks in a row. The middle peak (the 'head') is the highest, and the two "
              "outer peaks (the 'shoulders') are lower and roughly equal. A line joining the two "
              "dips between the peaks is called the 'neckline'.",
        means="Buyers pushed price to a new high (the head) but could not do it again (the right "
              "shoulder). A close below the neckline suggests the uptrend is turning into a downtrend.",
        target="Height from the head down to the neckline, subtracted from the breakout point.",
        stop="Just above the right shoulder. Going back above it would mean the sellers lost control.",
    ),
    "Inverse Head and Shoulders": dict(
        category="Reversal", bias="Bullish",
        looks="Three troughs in a row. The middle one (the 'head') is the lowest and the two outer "
              "troughs (the 'shoulders') are higher and roughly equal. The line joining the two "
              "bounces between them is the 'neckline'.",
        means="Sellers pushed price to a new low but could not do it again. A close above the "
              "neckline suggests a downtrend is turning into an uptrend.",
        target="Height from the head up to the neckline, added to the breakout point.",
        stop="Just below the right shoulder.",
    ),
    "Double Top": dict(
        category="Reversal", bias="Bearish",
        looks="Two peaks at about the same price with a dip between them, shaped like the letter 'M'.",
        means="Price hit the same ceiling twice and was pushed back both times. A close below the "
              "dip between the peaks (the 'neckline') suggests the uptrend is over.",
        target="Height from the peaks down to the neckline, subtracted from the neckline.",
        stop="Just above the higher of the two peaks.",
    ),
    "Double Bottom": dict(
        category="Reversal", bias="Bullish",
        looks="Two troughs at about the same price with a bounce between them, shaped like the letter 'W'.",
        means="Price found the same floor twice. A close above the bounce between the troughs (the "
              "'neckline') suggests the downtrend is over.",
        target="Height from the troughs up to the neckline, added to the neckline.",
        stop="Just below the lower of the two troughs.",
    ),
    "Triple Top": dict(
        category="Reversal", bias="Bearish",
        looks="Three peaks at about the same price, with two dips between them.",
        means="Price failed three times at the same ceiling. A close below the lowest dip suggests "
              "the uptrend is over.",
        target="Height from the peaks down to the support line, subtracted from the support line.",
        stop="Just above the highest of the three peaks.",
    ),
    "Triple Bottom": dict(
        category="Reversal", bias="Bullish",
        looks="Three troughs at about the same price, with two bounces between them.",
        means="Price held the same floor three times. A close above the highest bounce suggests "
              "the downtrend is over.",
        target="Height from the troughs up to the resistance line, added to the resistance line.",
        stop="Just below the lowest of the three troughs.",
    ),
    "Cup and Handle": dict(
        category="Reversal", bias="Bullish",
        looks="A rounded, U-shaped dip (the 'cup') that climbs back to its starting price, followed by "
              "a small, shallow pullback (the 'handle').",
        means="A slow, orderly recovery followed by a last brief shake-out. A close above the rim of "
              "the cup suggests a new move up.",
        target="Depth of the cup, added to the rim.",
        stop="Just below the lowest point of the handle.",
    ),
    "Rounding Bottom": dict(
        category="Reversal", bias="Bullish",
        looks="A long, smooth, bowl-shaped curve: price drifts down, flattens out, then drifts back up.",
        means="Selling slowly fades and buying slowly returns. A close above the starting level (the "
              "'lip') suggests a longer-term uptrend.",
        target="Depth of the bowl, added to the lip.",
        stop="Below the lowest price of the last part of the bowl.",
    ),
    "Rounding Top": dict(
        category="Reversal", bias="Bearish",
        looks="A long, smooth, upside-down bowl (a dome): price drifts up, flattens out, then drifts back down.",
        means="Buying slowly fades and selling slowly takes over. A close below the starting level "
              "suggests a longer-term downtrend.",
        target="Height of the dome, subtracted from the starting level.",
        stop="Above the highest price of the last part of the dome.",
    ),
    # ---------------- Continuation patterns ----------------
    "Bull Flag": dict(
        category="Continuation", bias="Bullish",
        looks="A sharp rise (the 'flagpole') followed by a short, gentle drift down inside two roughly "
              "parallel lines (the 'flag').",
        means="Traders paused to take some profit after a fast rise. A close above the top of the "
              "flag suggests the rise will continue.",
        target="Length of the flagpole, added to the breakout point.",
        stop="Just below the lowest point of the flag.",
    ),
    "Bear Flag": dict(
        category="Continuation", bias="Bearish",
        looks="A sharp fall (the 'flagpole') followed by a short, gentle drift up inside two roughly "
              "parallel lines (the 'flag').",
        means="A brief bounce after a fast fall. A close below the bottom of the flag suggests the "
              "fall will continue.",
        target="Length of the flagpole, subtracted from the breakout point.",
        stop="Just above the highest point of the flag.",
    ),
    "Bull Pennant": dict(
        category="Continuation", bias="Bullish",
        looks="A sharp rise followed by a small triangle where the swings get smaller and smaller.",
        means="A short pause while buyers and sellers balance out. A close above the top line "
              "suggests the rise will continue.",
        target="Length of the flagpole, added to the breakout point.",
        stop="Just below the lowest point of the pennant.",
    ),
    "Bear Pennant": dict(
        category="Continuation", bias="Bearish",
        looks="A sharp fall followed by a small triangle where the swings get smaller and smaller.",
        means="A short pause after a fast fall. A close below the bottom line suggests the fall "
              "will continue.",
        target="Length of the flagpole, subtracted from the breakout point.",
        stop="Just above the highest point of the pennant.",
    ),
    "Ascending Triangle": dict(
        category="Continuation", bias="Bullish",
        looks="A flat ceiling on top and a rising floor underneath (each dip is higher than the last).",
        means="Sellers keep selling at the same price, but buyers step in earlier and earlier. A close "
              "above the flat ceiling usually leads to a move up.",
        target="Height of the triangle at its widest point, added to the breakout point.",
        stop="Just below the most recent dip inside the triangle.",
    ),
    "Descending Triangle": dict(
        category="Continuation", bias="Bearish",
        looks="A flat floor underneath and a falling ceiling on top (each peak is lower than the last).",
        means="Buyers keep buying at the same price, but sellers get more and more eager. A close below "
              "the flat floor usually leads to a move down.",
        target="Height of the triangle at its widest point, subtracted from the breakout point.",
        stop="Just above the most recent peak inside the triangle.",
    ),
    "Rectangle": dict(
        category="Continuation", bias="Neutral",
        looks="Price bounces between a flat ceiling and a flat floor, like a box.",
        means="A pause where buyers and sellers are evenly matched. It most often breaks out in the "
              "same direction as the trend that came before it, but it can go either way.",
        target="Height of the box, added to (upward breakout) or subtracted from (downward breakout) "
               "the breakout point.",
        stop="The middle of the box. Falling back to the middle suggests the breakout has failed.",
    ),
    # ---------------- Bilateral patterns ----------------
    "Symmetrical Triangle": dict(
        category="Bilateral", bias="Neutral",
        looks="Peaks keep getting lower and dips keep getting higher, so the two lines squeeze together.",
        means="Neither side is in control and price is coiling up. The breakout can go either way; "
              "the direction of the first close outside the lines is what counts.",
        target="Height of the triangle at its widest point, measured from the breakout point in the "
               "direction of the breakout.",
        stop="Just beyond the most recent swing on the other side of the triangle.",
    ),
    "Rising Wedge": dict(
        category="Bilateral", bias="Bearish",
        looks="Both lines slope upward, but the lower line rises faster, so they squeeze together.",
        means="Price is still rising but each push up is weaker. It usually breaks downward.",
        target="Back to where the wedge began (its lowest starting point).",
        stop="Just above the most recent peak inside the wedge.",
    ),
    "Falling Wedge": dict(
        category="Bilateral", bias="Bullish",
        looks="Both lines slope downward, but the upper line falls faster, so they squeeze together.",
        means="Price is still falling but each push down is weaker. It usually breaks upward.",
        target="Back to where the wedge began (its highest starting point).",
        stop="Just below the most recent dip inside the wedge.",
    ),
}

STATUS_HELP = {
    "Forming": "The shape is in place but price has not yet closed beyond the breakout level. "
               "Nothing is confirmed yet - many patterns never break out.",
    "Confirmed": "Price closed beyond the breakout level, which confirms the pattern. "
                 "It has not yet reached the target or the stop-loss.",
    "Target reached": "After the breakout, price reached the projected target.",
    "Stopped out": "After the breakout, price turned around and hit the stop-loss first.",
    "Failed": "Price moved the wrong way through the stop-loss level before any breakout happened.",
    "Expired": "Price never broke out within a reasonable time, so the pattern no longer counts.",
}

GLOSSARY = [
    ("Ticker", "The short code for a stock or fund, for example AAPL for Apple or SPY for an S&P 500 fund."),
    ("Candlestick", "Each bar on the chart shows one period (for example one day). The thin line goes from "
                    "the lowest to the highest price. The thick part goes from the opening to the closing "
                    "price. Green means it closed higher than it opened; red means lower."),
    ("Volume", "How many shares were traded. Big moves on heavy volume are usually taken more seriously."),
    ("Moving average", "The average closing price over the last N periods. It smooths out the noise. "
                       "The 50 and 200 period averages are the most watched."),
    ("RSI", "Relative Strength Index, from 0 to 100. It compares recent gains with recent losses. "
            "Above 70 is called overbought; below 30 is called oversold."),
    ("MACD", "Moving Average Convergence Divergence. It is the gap between a fast (12) and a slow (26) "
             "moving average. When it crosses above its own 9-period average (the signal line), "
             "momentum is turning up."),
    ("ATR", "Average True Range: the typical size of one period's price swing. The app uses it to decide "
            "which swings are big enough to matter."),
    ("Swing high / swing low", "A turning point: a peak (swing high) or a trough (swing low) where price "
                               "reversed by a meaningful amount."),
    ("Breakout", "A close beyond the pattern's key line. This is the moment a pattern is 'confirmed'."),
    ("Entry (breakout level)", "The price of the key line at the breakout. Traders who act on patterns "
                               "usually buy or sell around this price."),
    ("Target (projected move)", "Where the 'measured move' rule says price may go after the breakout. "
                                "It is an estimate, not a promise."),
    ("Stop-loss", "A price where you would accept that the pattern was wrong and get out, to limit the loss."),
    ("Reward-to-risk", "Distance to the target divided by distance to the stop. 2.0 means the possible "
                       "gain is twice the possible loss. Below 1.0 means you risk more than you might gain."),
    ("Quality score", "0 to 100. How closely the shape matches the textbook definition (equal peaks, "
                      "clean lines, symmetry and so on). It is NOT the chance that the trade will work."),
    ("Sensitivity", "Low finds only big, obvious swings. High also finds smaller swings, which gives more "
                    "patterns but also more false alarms."),
]

DISCLAIMER = (
    "This app is a learning and research tool, not financial advice. Chart patterns are rules of thumb. "
    "They often fail, and they also show up by chance in completely random price data. Always do your own "
    "research and never risk money you cannot afford to lose."
)
