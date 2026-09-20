# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The primary user is Scott, reviewing Bitcoin and related assets on desktop and iPhone to understand long-cycle valuation, market regime, macro conditions, and investable context. The dashboard is also intended to remain accessible from other computers through its private ChatGPT Sites edition.

## Product Purpose

The dashboard combines repeatable cycle analysis for Bitcoin, gold, silver, the Magnificent Seven, Strategy, the S&P 500, and NASDAQ. It should help the user move from current market state to an informed investment posture without presenting model output as certainty or financial advice.

Success means the user can quickly identify the selected asset, understand its present valuation and regime, inspect the underlying charts and macro evidence, and understand what each number means in practical Bitcoin-investing terms.

## Positioning

Unlike a generic price terminal, the dashboard uses one consistent long-cycle interpretation framework across assets and then adds a Bitcoin-specific macro, fiscal, liquidity, volatility, and exchange-supply workspace. It translates raw metrics and historical percentiles into plain-language context while keeping sources and model limitations visible.

## Operating Context

- Used repeatedly as a personal research and decision-support tool.
- Viewed on desktop, iPhone, and remotely through a private hosted edition.
- Data refreshes locally several times per day while the Mac is awake and logged in.
- Charts support long-horizon comparison, with ten-year or maximum history where the source permits it.
- The user expects explanatory context beside exhibits: what the metric is, why it matters, how to read it, and an appropriately qualified investor posture.

## Capabilities and Constraints

- Preserve the existing asset universe, calculations, data sources, model logic, chart tabs, macro tabs, and explanatory content.
- Preserve the four key moving averages only: 50-day, 100-day, 200-day, and 200-week.
- Preserve the shared minus-two to plus-two interpretation scale where it is mathematically appropriate; clearly label context-only metrics that cannot be scored honestly.
- Preserve data provenance and limitations, including the distinction between tracked exchange custody inventory and coins actually offered for sale.
- Keep the interface responsive and touch-friendly; mobile must recompose rather than shrink the desktop layout.
- The hosted preview must not replace the approved live Sites deployment until the user explicitly approves it.
- This remains decision support, not financial advice or an automated trading system.

## Brand Commitments

- Product name: Multi-Asset Cycle Dashboard.
- The personal Obsidian Design Taste Library is the binding visual authority for the redesign.
- The redesign applies consistently across desktop, iPhone, and the private hosted edition.
- The user requested an approval preview before any live replacement or republishing.
- Voice should be direct, explanatory, calm, and analytically honest.

## Evidence on Hand

- Current working dashboard: `index.html`, `src/styles.css`, and `src/app.js`.
- Generated market and macro payloads under `public/data/`.
- Product and source documentation in `README.md`.
- Personal design evidence in the Obsidian Design Taste Library, including its architectural-editorial layout references, architectural grotesk typography, annotated linework, charcoal art direction, and the Inkwell/Lunar Eclipse/Crème Brûlée/Au Lait palette.
- Current desktop and mobile behavior can be inspected at `http://127.0.0.1:4174/`.
- The approved live hosted edition remains at `https://multi-asset-cycle-dashboard.scottleedavid.chatgpt.site/` and must not be overwritten during preview work.

## Product Principles

1. Explain the decision value of every number, not merely the calculation.
2. Let long-horizon evidence lead; avoid short-term noise and false precision.
3. Use one consistent analytical language while being honest when indicators are not comparable.
4. Preserve research depth without forcing the user to parse a wall of equally weighted panels.
5. Keep risk, provenance, and model limitations close to the claims they qualify.

## Accessibility & Inclusion

Maintain readable type, WCAG AA contrast for functional text and controls, visible keyboard focus, touch targets suitable for iPhone, reduced-motion support, and chart explanations that do not rely on colour alone.
