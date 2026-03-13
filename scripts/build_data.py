#!/usr/bin/env python3
import json
import sqlite3
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT.parent / "geopolitical_risk_dashboard" / "risk_index.db"
OUT_PATH = ROOT / "docs" / "data.json"

HKT = timezone(timedelta(hours=8))
CHOKEPOINT_API = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0/query"


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


def load_gsi_daily(days: int = 30):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    rows = cur.execute(
        """
        SELECT ts, index_value, market_count, total_liquidity
        FROM index_history
        WHERE ts >= strftime('%s','now') - ?
        ORDER BY ts ASC
        """,
        (days * 86400,),
    ).fetchall()
    con.close()

    if not rows:
        return [], None, None

    daily = OrderedDict()
    raw = []
    for ts, gsi, markets, liq in rows:
        dt = datetime.fromtimestamp(ts, HKT)
        day_key = dt.strftime("%Y-%m-%d")
        raw.append(
            {
                "ts": int(ts),
                "time_hkt": dt.strftime("%Y-%m-%d %H:%M"),
                "gsi": round(float(gsi), 4),
                "markets": int(markets),
                "liquidity": round(float(liq), 2),
            }
        )
        daily[day_key] = {
            "date": day_key,
            "gsi": round(float(gsi), 4),  # keep latest snapshot of each day
        }

    latest = raw[-1]
    prev = raw[-2] if len(raw) >= 2 else raw[-1]
    delta = round(latest["gsi"] - prev["gsi"], 4)
    return list(daily.values()), latest, delta


def load_hormuz_traffic_daily(days: int = 30):
    params = {
        "where": "portid='chokepoint6' AND date >= CURRENT_DATE - 30",
        "outFields": "date,portid,portname,n_total,n_tanker,capacity",
        "orderByFields": "date ASC",
        "f": "json",
    }
    js = requests.get(CHOKEPOINT_API, params=params, timeout=60).json()
    feats = js.get("features", [])
    out = []
    for f in feats:
        a = f["attributes"]
        dt = datetime.fromtimestamp(a["date"] / 1000, HKT)
        out.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "n_total": int(a.get("n_total") or 0),
                "n_tanker": int(a.get("n_tanker") or 0),
                "capacity": float(a.get("capacity") or 0),
                "portname": a.get("portname", "Strait of Hormuz"),
            }
        )
    return out


def main() -> None:
    gsi_daily, latest, delta = load_gsi_daily(days=30)
    traffic_daily = load_hormuz_traffic_daily(days=30)

    if not latest:
        raise SystemExit("No GSI history found")

    payload = {
        "title": "Strait of Hormuz Risk Tracker",
        "generated_at_hkt": datetime.now(HKT).strftime("%Y-%m-%d %H:%M:%S"),
        "sources": {
            "traffic": "IMF PortWatch Daily_Chokepoints_Data (public ArcGIS service)",
            "gsi": "Local geopolitical_risk_dashboard/risk_index.db",
        },
        "latest": {
            **latest,
            "delta": delta,
            "risk_level": risk_level(latest["gsi"]),
        },
        "gsi_daily": gsi_daily,
        "hormuz_traffic_daily": traffic_daily,
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
