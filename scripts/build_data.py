#!/usr/bin/env python3
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT.parent / "geopolitical_risk_dashboard" / "risk_index.db"
OUT_PATH = ROOT / "docs" / "data.json"

HKT = timezone(timedelta(hours=8))


def risk_level(gsi: float) -> str:
    if gsi >= 0.45:
        return "Extreme"
    if gsi >= 0.35:
        return "High"
    if gsi >= 0.25:
        return "Elevated"
    if gsi >= 0.15:
        return "Moderate"
    return "Low"


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    rows = cur.execute(
        """
        SELECT ts, index_value, market_count, total_liquidity
        FROM index_history
        ORDER BY ts DESC
        LIMIT 240
        """
    ).fetchall()
    con.close()

    if not rows:
        raise SystemExit("No index history found")

    rows = list(reversed(rows))
    series = [
        {
            "ts": int(ts),
            "time_hkt": datetime.fromtimestamp(ts, HKT).strftime("%Y-%m-%d %H:%M"),
            "gsi": round(float(gsi), 4),
            "markets": int(markets),
            "liquidity": round(float(liq), 2),
        }
        for ts, gsi, markets, liq in rows
    ]

    latest = series[-1]
    prev = series[-2] if len(series) >= 2 else series[-1]
    delta = round(latest["gsi"] - prev["gsi"], 4)

    payload = {
        "title": "Strait of Hormuz Risk Tracker",
        "generated_at_hkt": datetime.now(HKT).strftime("%Y-%m-%d %H:%M:%S"),
        "latest": {
            **latest,
            "delta": delta,
            "risk_level": risk_level(latest["gsi"]),
        },
        "series": series,
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
