# Strait of Hormuz Tracker

Simple GitHub Pages site that visualizes the latest Geopolitical Sentiment Index (GSI) as a proxy tracker for Strait of Hormuz risk sentiment.

## Update data

From this repo:

```bash
python3 scripts/build_data.py
```

This reads from `../geopolitical_risk_dashboard/risk_index.db` and writes `docs/data.json`.

## Publish

GitHub Pages serves from `/docs` on `main`.
