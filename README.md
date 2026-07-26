# Multi-Asset Cycle Dashboard

Central dashboard for repeating the Bitcoin cycle toolkit across multiple assets:

- Bitcoin (`BTC-USD`)
- Gold ETF proxy (`GLD`)
- Silver ETF proxy (`SLV`)
- Roundhill Magnificent Seven ETF (`MAGS`)
- S&P 500 Index (`^GSPC`)
- NASDAQ Composite (`^IXIC`)

## What it includes

Each asset gets the same core charting/readout stack:

- Log regression channel
- Rainbow / power-law percentile bands
- Dedicated price chart with 50D, 100D, 200D, and 200W moving averages
- RSI 14D
- Drawdown from all-time high
- Regime score
- Elliott Wave scenario lab with pivot map and confluence scoring
- Data provenance panel
- BTC macro domino sequence: ISM Manufacturing PMI, copper/gold breakout, BTC implied and 90-day realized volatility, plus WTI oil invalidation risk

## Data sources

- BTC: CoinMetrics community BTC CSV + Coinbase Exchange daily candles + Coinbase spot ticker.
- Non-BTC assets: Yahoo Finance no-key chart endpoint, with regular-market price overlaid as the provisional current row when available.

ETF proxies are used for gold/silver as requested: `GLD`, `SLV`.
Index levels are used for S&P 500 and NASDAQ as requested: `^GSPC`, `^IXIC`.

## Run

```bash
cd /Users/scott/Developer/Multi-Asset-Cycle-Dashboard
python3 scripts/fetch_assets.py
python3 scripts/build_indicators.py
python3 scripts/build_macro_cycle.py
python3 -m http.server 4174 --bind 127.0.0.1
```

Open:

```text
http://localhost:4174/
```

## Permanent local dashboard

The dashboard is served locally by macOS `launchd`:

- URL: `http://127.0.0.1:4174/`
- Server LaunchAgent: `~/Library/LaunchAgents/com.scott.multi-asset-cycle-dashboard.server.plist`
- Refresh LaunchAgent: `~/Library/LaunchAgents/com.scott.multi-asset-cycle-dashboard.refresh.plist`
- Server wrapper: `~/.hermes/bin/multi-asset-dashboard-server.sh`
- Refresh wrapper: `~/.hermes/bin/multi-asset-dashboard-refresh.sh`
- Health check: `~/.hermes/bin/multi-asset-dashboard-health.sh`
- Logs: `~/.hermes/logs/multi-asset-cycle-dashboard/`

Useful commands:

```bash
~/.hermes/bin/multi-asset-dashboard-health.sh
launchctl print gui/$(id -u)/com.scott.multi-asset-cycle-dashboard.server
launchctl print gui/$(id -u)/com.scott.multi-asset-cycle-dashboard.refresh
tail -80 ~/.hermes/logs/multi-asset-cycle-dashboard/refresh.log
```

## Scheduled refresh

The local refresh LaunchAgent runs three times daily — 6:00 AM, 12:00 PM, and 5:00 PM Eastern/Toronto time — while the Mac is awake and logged in:

```text
~/Library/LaunchAgents/com.scott.multi-asset-cycle-dashboard.refresh.plist
```

The script fetches current data for all assets and rebuilds dashboard JSON:

```text
~/.hermes/bin/multi-asset-dashboard-refresh.sh
```

It logs refresh output and errors to:

```text
~/.hermes/logs/multi-asset-cycle-dashboard/refresh.log
```

## Limitations

- Rainbow bands and log channels are historical visualizations, not predictive models.
- Yahoo Finance is a free no-key prototype source; it may occasionally rate-limit or change response shape.
- Current-day non-BTC values may be provisional regular-market prices until daily bars finalize.
- ISM Manufacturing PMI is currently an explicit manual, video-sourced snapshot in `data/manual/macro-cycle.json`; the dashboard labels it as non-live. Copper, gold, oil, DVOL, and realized volatility refresh automatically.
- Elliott Wave counts are algorithmic scenario candidates, not manual analyst-certified wave counts.
