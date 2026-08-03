# Multi-Asset Cycle Dashboard

Central dashboard for repeating the Bitcoin cycle toolkit across multiple assets:

- Bitcoin (`BTC-USD`)
- Gold ETF proxy (`GLD`)
- Silver ETF proxy (`SLV`)
- Roundhill Magnificent Seven ETF (`MAGS`)
- Strategy (formerly MicroStrategy), a Bitcoin treasury company (`MSTR`)
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
- Bitcoin-only macro workspace with liquidity, dollar, real-yield, financial-conditions, M2, oil, federal-debt, Treasury-absorption, foreign-holder, stablecoin, and exchange-supply views
- BTC macro domino sequence: ISM Manufacturing PMI, copper/gold breakout, BTC implied and 90-day realized volatility, plus WTI oil invalidation risk

## Data sources

- BTC: CoinMetrics community BTC CSV + Coinbase Exchange daily candles + Coinbase spot ticker.
- Non-BTC assets: Yahoo Finance no-key chart endpoint, with regular-market price overlaid as the provisional current row when available.
- Macro history: Federal Reserve/FRED, U.S. Treasury FiscalData, and Treasury International Capital (TIC).
- USD stablecoin supply: DefiLlama. This is labelled as shorter-history crypto liquidity rather than a ten-year macro series.
- Labelled BTC exchange balances and net flows: Glassnode when `GLASSNODE_API_KEY` is configured. Exchange custody inventory is not represented as coins currently offered for sale.

ETF proxies are used for gold/silver as requested: `GLD`, `SLV`.
Index levels are used for S&P 500 and NASDAQ as requested: `^GSPC`, `^IXIC`.
MSTR is categorized as a Bitcoin Treasury Company and uses Strategy's public equity price history.

## Run

```bash
cd /Users/scott/Developer/Multi-Asset-Cycle-Dashboard
python3 scripts/fetch_assets.py
python3 scripts/build_indicators.py
python3 scripts/build_macro_cycle.py
python3 scripts/fetch_macro_history.py
python3 scripts/build_macro_dashboard.py
python3 scripts/validate_macro_dashboard.py
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

It also refreshes and validates the two Bitcoin macro payloads:

```text
public/data/btc-macro.json
public/data/btc-market-supply.json
```

### BTC exchange-supply data

The BTC Market Supply tab uses Coin Metrics Community API metric `SplyExNtv` to show a consistent daily history of BTC held in identified exchange wallets. The 10Y view is available without a paid API key. Label coverage can change over time, and exchange custody inventory is not the amount currently posted in sell orders.

### Foreign holders of U.S. Treasury debt

The Fiscal & Holders tab combines the current TIC Major Foreign Holders table with its official monthly history. It ranks the 15 largest reported holders and shows three-month and twelve-month buying/selling trends. Treasury notes that TIC country attribution is primarily custodial; holdings reported in the United Kingdom, Belgium, Luxembourg, the Cayman Islands, and other financial centers may belong to investors elsewhere.

It logs refresh output and errors to:

```text
~/.hermes/logs/multi-asset-cycle-dashboard/refresh.log
```

## Limitations

- Rainbow bands and log channels are historical visualizations, not predictive models.
- Yahoo Finance is a free no-key prototype source; it may occasionally rate-limit or change response shape.
- Current-day non-BTC values may be provisional regular-market prices until daily bars finalize.
- ISM Manufacturing PMI is currently an explicit manual, video-sourced snapshot in `data/manual/macro-cycle.json`; the dashboard labels it as non-live. Copper, gold, oil, DVOL, and realized volatility refresh automatically.
- Macro relationships with Bitcoin are regime-dependent and are displayed as decision context rather than causal trading rules.
- Treasury country holdings can reflect custodians rather than ultimate beneficial owners.
- Glassnode address labels may be revised, and exchange custody inventory is not equivalent to executable sell-side liquidity.
- Elliott Wave counts are algorithmic scenario candidates, not manual analyst-certified wave counts.
