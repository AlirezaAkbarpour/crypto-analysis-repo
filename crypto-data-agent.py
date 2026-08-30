#!/usr/bin/env python3
"""Local crypto analytics plus optional OpenAI-compatible model analysis.

Usage:
  python crypto-data-agent.py prices.csv --report report.json
  python crypto-data-agent.py prices.csv --question "Is momentum improving?"

Environment for model mode:
  MODEL_API_KEY       API key (never printed or written to reports)
  MODEL_BASE_URL      OpenAI-compatible base URL, default https://api.openai.com/v1
  MODEL_NAME          Model name, default gpt-4o-mini
"""
import argparse
import csv
import json
import math
import os
import statistics
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

PROMPT_PATH = Path(__file__).with_name("prompts") / "crypto-analysis-prompt.md"


def load_prices(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = row.get("Date") or row.get("date")
            raw = row.get("Price USD") or row.get("price_usd") or row.get("price")
            if not d or raw is None:
                continue
            try:
                rows.append((datetime.strptime(d[:10], "%Y-%m-%d").date(), float(raw)))
            except ValueError:
                continue
    rows.sort()
    if len(rows) < 3:
        raise SystemExit("Need at least 3 valid Date/Price USD rows.")
    return rows


def pct(a, b):
    return (b / a - 1) if a else 0.0


def sma(values, n):
    return sum(values[-n:]) / n if len(values) >= n else None


def max_drawdown(values):
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        worst = min(worst, pct(peak, value))
    return worst


def pearson(x, y):
    if len(x) < 2:
        return None
    mx, my = statistics.mean(x), statistics.mean(y)
    den = math.sqrt(sum((v - mx) ** 2 for v in x) * sum((v - my) ** 2 for v in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / den if den else 0.0


def build_report(rows):
    dates = [d.isoformat() for d, _ in rows]
    values = [p for _, p in rows]
    returns = [pct(values[i - 1], values[i]) for i in range(1, len(values))]
    positive = [r for r in returns if r > 0]
    negative = [r for r in returns if r < 0]
    events = sorted(
        ({"date": dates[i], "return": returns[i - 1], "price_usd": values[i]} for i in range(1, len(values))),
        key=lambda x: x["return"], reverse=True,
    )
    monthly = {}
    for i, d in enumerate(dates):
        monthly.setdefault(d[:7], []).append(i)
    monthly_report = {}
    for month, indexes in monthly.items():
        first, last = indexes[0], indexes[-1]
        monthly_report[month] = {
            "return": pct(values[first], values[last]),
            "days": len(indexes),
        }
    return {
        "data_range": {"start": dates[0], "end": dates[-1], "rows": len(rows)},
        "price": {"first_usd": values[0], "last_usd": values[-1], "min_usd": min(values), "max_usd": max(values)},
        "returns": {
            "total": pct(values[0], values[-1]),
            "mean_daily": statistics.mean(returns),
            "mean_abs_daily": statistics.mean(abs(r) for r in returns),
            "daily_stdev": statistics.stdev(returns) if len(returns) > 1 else 0,
            "positive_days": len(positive),
            "negative_days": len(negative),
            "max_drawdown": max_drawdown(values),
            "sma_7": sma(values, 7),
            "sma_30": sma(values, 30),
        },
        "largest_growth_days": events[:10],
        "largest_decline_days": list(reversed(events[-10:])),
        "monthly": monthly_report,
        "limitations": ["Price-only analysis; volume, liquidity, news, and on-chain data are not included.", "Historical patterns do not predict future returns."],
    }


def load_prompt():
    return PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else "Analyze the supplied crypto report conservatively."


def ask_model(report, question):
    api_key = os.getenv("MODEL_API_KEY")
    if not api_key:
        raise SystemExit("MODEL_API_KEY is required for --question mode.")
    base = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("MODEL_NAME", "gpt-4o-mini")
    body = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": load_prompt()},
            {"role": "user", "content": json.dumps({"question": question, "report": report}, ensure_ascii=False)},
        ],
    }
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.load(response)
    return result["choices"][0]["message"]["content"]


def main():
    parser = argparse.ArgumentParser(description="Analyze crypto price CSVs and optionally ask a data model.")
    parser.add_argument("csv_file")
    parser.add_argument("--report", default="crypto-report.json")
    parser.add_argument("--question")
    args = parser.parse_args()
    report = build_report(load_prices(args.csv_file))
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.question:
        print("\nMODEL_ANALYSIS\n" + ask_model(report, args.question))


if __name__ == "__main__":
    main()
