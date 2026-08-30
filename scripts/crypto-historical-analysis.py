#!/usr/bin/env python3
"""
Download and analyze historical daily crypto prices from CoinGecko.
Compares token returns with BTC to detect correlation and lag relationships.

Usage:
  python crypto-historical-analysis.py <coin_id> <days> <output.csv>

Example:
  python crypto-historical-analysis.py robo-token-2 730 fabric-prices.csv

Output:
  - CSV file with Date and Price USD columns.
  - Terminal output: correlation, volatility, lag analysis.
"""

import csv
import json
import math
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path


API = "https://api.coingecko.com/api/v3"


def fetch(coin_id, days):
    """Fetch daily OHLC prices from CoinGecko."""
    url = f"{API}/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)["prices"]
    except urllib.error.HTTPError as e:
        raise SystemExit(f"✗ API error: HTTP {e.code} — rate limit or invalid coin ID?")
    except Exception as e:
        raise SystemExit(f"✗ Network error: {e}")


def as_dict(points):
    """Convert [(timestamp_ms, price), ...] to {date_str: price}."""
    return {
        datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d"): price
        for ts, price in points
    }


def daily_returns(prices, dates):
    """Calculate close-to-close daily returns."""
    returns = []
    for i in range(1, len(dates)):
        prev, curr = prices[dates[i - 1]], prices[dates[i]]
        if prev > 0:
            returns.append(curr / prev - 1)
    return returns


def pearson(x, y):
    """Pearson correlation coefficient."""
    if len(x) < 2 or len(y) < 2:
        return 0.0
    mx, my = sum(x) / len(x), sum(y) / len(y)
    vx = sum((v - mx) ** 2 for v in x)
    vy = sum((v - my) ** 2 for v in y)
    if vx == 0 or vy == 0:
        return 0.0
    return sum((x[i] - mx) * (y[i] - my) for i in range(len(x))) / math.sqrt(vx * vy)


def main():
    if len(sys.argv) != 4:
        print("Usage: crypto-historical-analysis.py <coin_id> <days> <output.csv>")
        print("Example: crypto-historical-analysis.py robo-token-2 730 prices.csv")
        raise SystemExit(1)

    coin_id, days_str, output_path = sys.argv[1], sys.argv[2], Path(sys.argv[3])

    try:
        days = int(days_str)
    except ValueError:
        raise SystemExit(f"✗ days must be an integer, got: {days_str}")

    # Fetch token and BTC data
    print(f"⏳ Fetching {days}-day history for {coin_id}...", file=__import__("sys").stderr)
    token_prices = as_dict(fetch(coin_id, days))
    btc_prices = as_dict(fetch("bitcoin", days))

    # Align dates (common to both token and BTC)
    common_dates = sorted(set(token_prices) & set(btc_prices))
    if not common_dates:
        raise SystemExit("✗ No overlapping dates between token and BTC.")

    print(f"✓ {len(token_prices)} token prices, {len(btc_prices)} BTC prices")
    print(f"✓ {len(common_dates)} common dates: {common_dates[0]} to {common_dates[-1]}")

    # Save token prices to CSV
    with output_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Price USD"])
        for date in common_dates:
            w.writerow([date, token_prices[date]])
    print(f"✓ Saved to {output_path}")

    # Compute returns
    token_ret = daily_returns(token_prices, common_dates)
    btc_ret = daily_returns(btc_prices, common_dates)

    # Statistics
    token_vol = sum(abs(r) for r in token_ret) / len(token_ret) if token_ret else 0
    btc_vol = sum(abs(r) for r in btc_ret) / len(btc_ret) if btc_ret else 0
    corr = pearson(token_ret, btc_ret)

    print(f"\n📊 ANALYSIS RESULTS:")
    print(f"  TOKEN_COIN_ID {coin_id}")
    print(f"  PRICE_RANGE ${min(token_prices.values()):.8f} → ${max(token_prices.values()):.8f}")
    print(f"  CURRENT_PRICE ${token_prices[common_dates[-1]]:.8f}")
    print(f"  PEARSON_DAILY {corr:.4f}")
    print(f"  TOKEN_MEAN_ABS_DAILY_RETURN {token_vol:.4%}")
    print(f"  BTC_MEAN_ABS_DAILY_RETURN {btc_vol:.4%}")
    print(f"  VOLATILITY_RATIO {token_vol / btc_vol:.2f}x")

    # Lag analysis
    print(f"\n  LAG_ANALYSIS (correlation at offset days):")
    for lag in range(-7, 8):
        pairs = [
            (token_ret[i], btc_ret[i - lag])
            for i in range(max(0, lag), min(len(token_ret), len(btc_ret) + lag))
        ]
        if pairs:
            lag_corr = pearson([p[0] for p in pairs], [p[1] for p in pairs])
            print(f"    LAG_{lag:+d}d: {lag_corr:.4f}")

    # Monthly breakdown
    print(f"\n  MONTHLY_RETURNS:")
    monthly = defaultdict(list)
    for date in common_dates:
        month = date[:7]
        monthly[month].append(date)

    for month in sorted(monthly):
        dates = monthly[month]
        token_m = (token_prices[dates[-1]] / token_prices[dates[0]] - 1) * 100
        btc_m = (btc_prices[dates[-1]] / btc_prices[dates[0]] - 1) * 100
        print(f"    {month}: TOKEN {token_m:+.2f}% | BTC {btc_m:+.2f}%")


if __name__ == "__main__":
    main()
