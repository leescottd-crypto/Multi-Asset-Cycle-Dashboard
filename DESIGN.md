---
name: Multi-Asset Cycle Dashboard
description: A continuous petroleum-dark market instrument for reading cycle state, chart evidence, interpretation, and macro confirmation.
colors:
  petroleum-canvas: "#07181c"
  petroleum-deep: "#051317"
  petroleum-panel: "#0a1e22"
  petroleum-raised: "#0d2428"
  chart-canvas: "#08191d"
  warm-ivory: "#e6dac6"
  bright-ivory: "#f0e6d5"
  muted-stone: "#a9a99f"
  muted-stone-dark: "#747c78"
  signal-amber: "#d58b35"
  signal-amber-soft: "#b97831"
  supportive-sage: "#657f69"
  restrictive-rust: "#9b4f3f"
  mixed-sand: "#a99a6c"
  focus-amber: "#efad5c"
  rule: "rgba(230, 218, 198, .20)"
  rule-strong: "rgba(230, 218, 198, .34)"
  chart-price: "#f6f5f2"
  chart-trend: "#a27b5b"
  chart-accumulation: "#8fa184"
  chart-deep-value: "#789294"
  chart-take-chips: "#b06f60"
  chart-ma-50d: "#8fb8b6"
  chart-ma-100d: "#d1a16d"
  chart-ma-200d: "#c18aa6"
  chart-ma-200w: "#8fa184"
typography:
  display:
    fontFamily: '"Atlas Condensed", "Atlas Sans", "Helvetica Neue", Arial, sans-serif'
    fontSize: "clamp(54px, 5vw, 82px)"
    fontWeight: 520
    lineHeight: 1
    letterSpacing: "-0.04em"
  headline:
    fontFamily: '"Atlas Condensed", "Atlas Sans", "Helvetica Neue", Arial, sans-serif'
    fontSize: "clamp(42px, 4vw, 65px)"
    fontWeight: 540
    lineHeight: 0.95
    letterSpacing: "-0.04em"
  title:
    fontFamily: '"Atlas Condensed", "Atlas Sans", "Helvetica Neue", Arial, sans-serif'
    fontSize: "24px"
    fontWeight: 650
    lineHeight: 1.1
    letterSpacing: "-0.035em"
  body:
    fontFamily: '"Atlas Sans", "Helvetica Neue", Arial, sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: '"Atlas Sans", "Helvetica Neue", Arial, sans-serif'
    fontSize: "10px"
    fontWeight: 580
    lineHeight: 1.4
    letterSpacing: "0.02em"
  mark:
    fontFamily: "Georgia, serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.1em"
rounded:
  square: "0"
spacing:
  hairline: "1px"
  xs: "6px"
  sm: "10px"
  md: "18px"
  lg: "28px"
  xl: "36px"
  section: "45px"
components:
  navigation-link:
    backgroundColor: "transparent"
    textColor: "{colors.warm-ivory}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "0 10px"
    height: "64px"
  outline-control:
    backgroundColor: "transparent"
    textColor: "{colors.warm-ivory}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "0 10px"
    height: "44px"
  chart-tab:
    backgroundColor: "transparent"
    textColor: "{colors.muted-stone}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    height: "44px"
  asset-cell:
    backgroundColor: "transparent"
    textColor: "{colors.warm-ivory}"
    rounded: "{rounded.square}"
    padding: "12px 19px 10px"
    height: "96px"
  interpretation-score:
    backgroundColor: "transparent"
    textColor: "{colors.warm-ivory}"
    rounded: "{rounded.square}"
    padding: "5px 7px"
    height: "32px"
---

# Design System: Multi-Asset Cycle Dashboard

## Overview

**Creative North Star: "The Petroleum Market Instrument"**

The approved A system is one continuous analytical instrument. A deep petroleum field carries warm ivory type, hairline brass-toned rules, and scarce amber signal marks; its density feels closer to a calibrated terminal or architectural drawing than to a collection of finance widgets. The visual story is fixed: read present state, test it against the dominant chart, interpret the evidence beside it, compare the asset strip, then confirm or challenge the conclusion with macro evidence.

The chart-first state / chart / interpretation topology is the signature. Sections remain visibly connected through shared edges and ruled bands rather than detached cards. This documentation records the completed `design-preview/` A system only: it is the approved propagation source, but the root implementation and Sites-hosted edition remain unchanged until the user separately authorizes propagation.

**Key Characteristics:**

- Deep petroleum canvas with warm ivory data typography.
- Amber reserved for the active or decision-relevant datum.
- Square controls, ruled topology, and near-zero elevation.
- State rail, dominant chart, and adjacent interpretation as one reading sequence.
- Asset comparison followed by Bitcoin macro confirmation evidence.
- Responsive iPhone recomposition, not desktop shrinkage.

## Colors

Petroleum and ivory carry the interface; amber identifies where to look now, while sage, rust, sand, and stable chart-series colours preserve analytical meaning.

### Primary

- **Petroleum Canvas / Deep / Panel / Raised:** The continuous page field, masthead, state rail, and subtle tonal bands. These remain closely related so the interface reads as one instrument.
- **Signal Amber / Signal Amber Soft:** Active navigation rules, selected asset marks, current scale positions, interpretation headings, chart reference lines, selection, and scrollbars.

### Secondary

- **Supportive Sage:** Supportive macro conditions, the accumulation band, and the 200-week moving average where series identity applies.
- **Restrictive Rust:** Restrictive macro conditions and upper-risk semantics.
- **Mixed Sand:** Mixed or indeterminate macro state.
- **Focus Amber:** The dedicated keyboard-focus outline, brighter than ordinary amber so focus remains unmistakable.

### Neutral

- **Warm Ivory / Bright Ivory:** Functional text, current values, section titles, price lines, and high-priority data.
- **Muted Stone / Muted Stone Dark:** Dates, sources, helper copy, inactive controls, axes, and quiet metadata.
- **Rule / Rule Strong:** Internal subdivisions and major boundaries.
- **Chart Canvas:** The plot field; it is only slightly distinct from the page so charts stay integrated.

**The Scarce Signal Rule.** Amber marks the active, selected, or decision-relevant datum; it does not wash whole panels or decorate every heading.

**The Meaning Beyond Colour Rule.** Every semantic colour is paired with a label, number, marker position, line style, arrow, or legend key.

### Chart Palette

Price remains the brightest line. Trend, accumulation, deep value, and take-chips bands keep stable identities, with secondary sigma bands differentiated by dotted line styles. Moving averages are exactly 50D, 100D, 200D, and 200W; their series colours and the dashed 200W treatment remain stable across charts, legends, hover values, and written descriptions.

## Typography

**Display and Headline Font:** Atlas Condensed, implemented with the bundled Roboto Condensed variable WOFF2, then Atlas Sans, Helvetica Neue, Arial, and sans-serif fallbacks.

**Body and Label Font:** Atlas Sans, implemented with the bundled variable Geist file, then Helvetica Neue, Arial, and sans-serif fallbacks.

**Brand Mark Font:** Georgia, serif.

**Character:** Condensed headings and large tabular-feeling values make the instrument dense without feeling cramped. Warm ivory softens the terminal character; small neutral labels behave like drawing annotations, while amber labels are reserved for interpretation and state.

### Hierarchy

- **Display:** Cycle position and major numeric evidence; tight, condensed, and visually dominant.
- **Headline:** Selected asset name and price; uppercase where the implemented state rail uses it.
- **Title:** Section and ledger titles; often uppercase in the evidence bands.
- **Body:** Explanations and analytical context; short lines and compact paragraphs keep evidence scannable.
- **Label:** Navigation, dates, sources, range controls, chart legends, units, and metadata; uppercase only for terse annotations.
- **Mark:** The `M | A` monogram only; do not extend the serif voice into analytical content.

**The Numbers Lead Rule.** Lead with the current value, then state or unit, context, interpretation, source, and limitation in descending visual weight.

## Layout

The canvas is capped at 2048px with a 64px sticky masthead and narrow outer breathing room. The first analytical band is a chart-first workspace: a 330px current-state rail at left, the dominant chart field in the centre, and a 360px interpretation column inside the chart pane at right. The plot stays at least 470px tall on desktop. This state / chart / interpretation relationship is a single topology, not three equal cards.

The ruled seven-asset strip follows the workspace and preserves BTC, Gold, Silver, MAGS, MSTR, S&P 500, and NASDAQ as one horizontal comparison band. Bitcoin then reveals the Macro Evidence band: four minimum-255px historical evidence columns followed by a wider heatmap, before the cycle ledger, metric notes, detailed macro workspace, and research notes. The asset strip comes before macro evidence so comparison precedes confirmation.

At 1460px the state rail narrows to 285px and interpretation to 310px. At 1080px navigation becomes a menu, chart controls move into normal flow, and interpretation drops beneath the chart while the 240px state rail remains beside it. At 760px the interface recomposes: the masthead becomes static; state becomes a compact horizontal summary; explanatory rail detail is withheld from the first mobile viewport; the chart is 390px tall; tabs and controls scroll; asset cells become a 170px snap row; macro evidence becomes 300px snapping columns with a wider heatmap; cycle columns become a 220px horizontal sequence; and metric and research grids become ruled vertical passages.

**The Evidence Order Rule.** Preserve the reading order: state and chart interpretation, asset strip, macro evidence, cycle history, metric detail, and research context.

**The Recomposition Rule.** Mobile changes hierarchy and flow; it never scales the full desktop composition into an unreadable miniature.

## Elevation & Depth

There are no card shadows. Depth comes from neighboring petroleum tones, a restrained radial atmosphere near the top of the canvas, sticky masthead translucency, active outlines, and differences between ordinary and strong rules. The chart is integrated rather than floated; glow, glossy gradients, and glass cards do not belong.

**The Flat-by-Construction Rule.** A region earns separation through adjacency, tone, rule weight, or active state—not a floating shadow.

## Shapes

The form language is square and drafted. Controls, tabs, asset cells, score fields, charts, metric regions, and content containers use zero radius. One-pixel rules create the recurring silhouette. Circular geometry is limited to data-position markers and the tiny information affordance; it is semantic punctuation, not a general component style.

## Components

### Navigation

- **Style:** A 64px ruled masthead with the serif `M | A` mark, direct product name, centred section links, and quiet date/actions.
- **Active / Hover:** The active section uses a 2px amber bottom rule; hover shifts the label to amber.
- **Mobile:** At 1080px and below, links move into a 220px square petroleum menu. The menu control keeps a 44px minimum height.

### Outline Controls

- **Shape:** Square with a one-pixel strong rule and transparent fill.
- **Size:** At least 44px high and 44px wide where compact.
- **States:** Active range controls use an amber bottom edge and bright ivory text. Keyboard focus uses a 2px Focus Amber outline with 3px offset.

### Chart Tabs

- **Style:** Transparent 44px controls on one continuous bottom rule.
- **State:** Inactive labels use Muted Stone; the active tab uses Bright Ivory plus a 2px Signal Amber underline.
- **Behavior:** Arrow keys move between tabs, selection state and tabpanel visibility stay synchronized, and mobile preserves labels in a horizontal scroll row.

### Current-State Rail

- **Content:** Asset identity, price, source, cycle position, zone, a -2 to +2 scale, trend-distance context, and compact facts.
- **Hierarchy:** The cycle score is the largest datum; amber names the zone and locates the marker.
- **Mobile:** Asset, price, and cycle position become a compact summary; secondary source, facts, and prose move out of the first viewport.

### Seven-Asset Strip

- **Shape:** Seven 96px-high square cells connected by vertical rules; no gaps and no detached cards.
- **Content:** Symbol and unit, price, regime, and cycle value.
- **State:** Hover adds only a faint ivory wash. Active state keeps the petroleum field, adds an amber outline and 3px left datum bar, and turns the symbol amber.
- **Mobile:** Fixed 170px cells form a touch-friendly horizontal snap row.

### Chart and Interpretation

- **Chart:** The dominant dark plot carries range, scale, fullscreen, accessible name, legend, and nearby written explanation. Mobile hides crowded right-axis series labels while preserving legends and prose.
- **Interpretation:** A ruled margin answers cycle interpretation, what it shows, why it matters, current read, investor posture, and method. It sits beside the plot on wide screens and directly below it on narrower screens.
- **Moving averages:** Show only 50D, 100D, 200D, and 200W. If a 200W series lacks enough history, say so instead of inventing a line.

### Macro Evidence Ledger

- **Structure:** Four shallow ten-year evidence charts and one direction heatmap share one ruled band.
- **Content:** Each evidence column includes title, current value, observation context, labelled axes, amber history line, source, and cadence.
- **Meaning:** Heatmap states are labelled supportive, mixed, or restrictive; colour is supplementary, and period change uses the indicator's native meaningful unit.
- **Mobile:** Evidence columns snap horizontally with the following column visible as a cue.

### Accessibility and Motion

- Use semantic buttons, links, tablists, tabs, and tabpanels with synchronized `aria-selected`, `aria-controls`, `aria-pressed`, `hidden`, and roving `tabindex` state.
- Preserve WCAG AA contrast, visible focus, 44px controls, logical DOM order, touch-safe horizontal scrolling, chart names, legends, and adjacent written interpretation.
- Reduced-motion preference disables smooth scrolling and reduces transitions and animation to effectively instant.

## Do's and Don'ts

### Do

- **Do** preserve the chart-first state / chart / interpretation topology and the full evidence order.
- **Do** keep amber scarce and bind it to active state, a current datum, or an analytical reference.
- **Do** preserve the seven-asset universe, the shared -2 to +2 scale where mathematically valid, and exactly four moving averages: 50D, 100D, 200D, and 200W.
- **Do** recompose iPhone layouts into compact summaries, scrollable evidence bands, and stacked ruled passages.
- **Do** keep sources, limitations, and investor interpretation adjacent to the evidence they qualify.
- **Do** treat `design-preview/` and its A-system screenshots as the design authority for later propagation.

### Don't

- **Don't** introduce rounded card grids, pills as the dominant grammar, shadows, neon glow, or generic finance-dashboard gradients.
- **Don't** turn amber into a broad decorative fill or use colour as the only carrier of meaning.
- **Don't** add moving-average series beyond 50D, 100D, 200D, and 200W.
- **Don't** score context-only indicators or present historical cycle framing as a deterministic forecast.
- **Don't** copy desktop dimensions onto iPhone without recomposition.
- **Don't** edit, replace, publish, or imply propagation to the root dashboard or Sites-hosted edition without a separate explicit approval.
