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
- 50D, 100D, 200D, and 200W moving averages
- RSI 14D
- Drawdown from all-time high
- Regime score
- Elliott Wave scenario lab with pivot map and confluence scoring
- Data provenance panel

## Data sources

- BTC: CoinMetrics community BTC CSV + Coinbase Exchange daily candles + Coinbase spot ticker.
- Non-BTC assets: Yahoo Finance no-key chart endpoint, with regular-market price overlaid as the provisional current row when available.

ETF proxies are used for gold/silver as requested: `GLD`, `SLV`.
Index levels are used for S&P 500 and NASDAQ as requested: `^GSPC`, `^IXIC`.

## Run

```bash
cd /Users/scottlee/Documents/Playground/multi-asset-cycle-dashboard
python3 scripts/fetch_assets.py
python3 scripts/build_indicators.py
python3 -m http.server 4174 --bind 127.0.0.1
```

Open:

```text
http://localhost:4174/
```

## Hourly refresh

Hermes cron runs the refresh script hourly from 5am through 6pm:

```text
/Users/scottlee/.hermes/scripts/update-multi-asset-cycle-dashboard.sh
```

The script fetches current data for all assets and rebuilds dashboard JSON.
It stays silent on success and reports logs only on failure.

## Limitations

- Rainbow bands and log channels are historical visualizations, not predictive models.
- Yahoo Finance is a free no-key prototype source; it may occasionally rate-limit or change response shape.
- Current-day non-BTC values may be provisional regular-market prices until daily bars finalize.
- Elliott Wave counts are algorithmic scenario candidates, not manual analyst-certified wave counts.
