# Reserve holdings

Local original and A-design preview use `src/reserve-holdings.js`, the existing
Lightweight Charts runtime, and `public/data/reserve-holdings.json`. No site was
deployed and no new scheduled task was enabled for this exhibit.

## Definition

Three lines, each quarter-end value divided by the same WGC `World` total-reserves
value (USD millions). The Treasury source is TIC Table 3, code 99990 (foreign
official, including bills, bonds and notes), not all foreign investors. Gold is
WGC's IMF World monetary gold aggregate, not a sum of incomplete country rows.
Bitcoin is a fixed four-government reported sample, not an official-reserve
component. It includes provider estimates and possible seized assets. The lines
are not a portfolio allocation and do not sum to 100%. Changes reflect valuation
as well as holdings changes. This exhibit does not affect Bitcoin scoring.

The WGC workbook contains history from 2000. The plotted common Treasury/gold
history starts in 2020, the start of the selected TIC file. Bitcoin uses exact
quarter-end matches in the free one-year CoinGecko history, beginning Q3 2025.
Earlier Bitcoin periods are null. No backward extrapolation or zero filling.

## Refresh

Run `python scripts/reserve_holdings.py --gold-workbook PATH` to import a new WGC
quarterly workbook and refresh other sources. Requires openpyxl for import.
Subsequent `python scripts/reserve_holdings.py` runs reuse the extracted gold
seed; they do not claim to update WGC. All network reads retain TLS verification.
Invalid/failed input stops before replacing the public snapshot. Public output
is atomically replaced only after validation. Previously verified Bitcoin dates
outside the rolling free window are preserved for the same country coverage.

Gold source is manually supplied; the original workbook remains unchanged and
is not copied into public assets. Only the world aggregate extract is retained,
with source filename and SHA-256 for provenance. The earlier two-line
`reserve-shift.json` snapshot is preserved but no longer used by the displayed
Reserve Shift pane.

Always-on refresh and Sites publication remain separate unfinished work. A new
cloud scheduler and authenticated publishing path must be resolved before
claiming that data refreshes while the Mac is off. The existing local refresh
wrapper has not been changed to run this script.
# Historical extension

The exhibit now uses the Treasury MFH historical archive from March 2000,
joined at actual quarter ends to the WGC World gold and total-reserves rows.
Archive values are billions of dollars, converted to millions before joining.
The first occurrence of duplicate months is the newer benchmark; the obsolete
comparison column is excluded. Current Table 3 overrides overlapping archive
dates from 2020. No Treasury quarters or pre-coverage Bitcoin balances are filled.

Pre-December 2011 Treasury figures use annual surveys advanced with monthly
transactions; later observations use SLT holdings. Benchmark revisions may cause
discontinuities and must not be interpreted as capital flows. The chart retains
this caveat visibly and in its source details.
