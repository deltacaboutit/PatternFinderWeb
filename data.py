"""
data.py - Gets price data for the app.

Two ways to get data:
  1. fetch_prices()  downloads it from Yahoo Finance (needs internet).
  2. load_csv()      reads a file you saved yourself (works offline).

Both return a table (a pandas "DataFrame") with one row per time period
(for example, one row per day) and these columns:
  Open   - the first price of the period
  High   - the highest price of the period
  Low    - the lowest price of the period
  Close  - the last price of the period
  Volume - how many shares changed hands
"""

import pandas as pd

COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

# Yahoo Finance only keeps hourly data for about the last two years.
HOURLY_MAX_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y"}


class DataError(Exception):
    """A friendly error we can show directly to the user."""


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the five columns we need, remove empty rows and time-zone labels."""
    # Some versions of yfinance return two-level column names; flatten them.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise DataError("The data is missing these columns: " + ", ".join(missing))

    df = df[COLUMNS].copy()
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df["Volume"] = df["Volume"].fillna(0)

    idx = pd.to_datetime(df.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    df.index = idx
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def fetch_prices(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Download price history for one ticker symbol from Yahoo Finance."""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise DataError("Please type a ticker symbol, for example AAPL.")

    if interval == "1h" and period not in HOURLY_MAX_PERIODS:
        raise DataError(
            "Yahoo Finance only keeps hourly data for about 2 years. "
            "Please pick a period of 2y or shorter, or switch to daily data."
        )

    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - only when setup was skipped
        raise DataError(
            "The 'yfinance' package is not installed. "
            "Run Start_PatternFinder.bat again to install it."
        ) from exc

    try:
        raw = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
    except Exception as exc:  # network problems, Yahoo changes, rate limits ...
        raise DataError(
            f"Could not download data for {ticker}. Check your internet connection "
            f"and try again in a minute.\n\nDetails: {exc}"
        ) from exc

    if raw is None or raw.empty:
        raise DataError(
            f"Yahoo Finance returned no data for '{ticker}'. "
            "Please check the ticker symbol (for example AAPL, MSFT or SPY)."
        )
    return _clean(raw)


def load_csv(path: str) -> pd.DataFrame:
    """Read price data from a CSV file.

    The file needs a date column (named Date, Datetime or Time) and the columns
    Open, High, Low, Close and Volume. Upper or lower case does not matter.
    """
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        raise DataError(f"Could not read the file.\n\nDetails: {exc}") from exc

    rename = {}
    for col in raw.columns:
        key = str(col).strip().lower().replace(" ", "").replace("_", "")
        if "." in key:  # e.g. "AAPL.Close" -> "close"
            key = key.split(".")[-1]
        if key in ("date", "datetime", "time", "timestamp"):
            rename[col] = "Date"
        elif key in ("adjclose",):
            rename[col] = "AdjClose"
        else:
            for wanted in COLUMNS:
                if key == wanted.lower():
                    rename[col] = wanted
    raw = raw.rename(columns=rename)

    if "Date" not in raw.columns:
        raise DataError("The CSV file needs a column called 'Date'.")
    if "Volume" not in raw.columns:
        raw["Volume"] = 0

    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce", utc=False)
    raw = raw.dropna(subset=["Date"]).set_index("Date")
    return _clean(raw)
