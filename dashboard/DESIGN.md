---
name: TR-BOT/2 Board
description: Read-only quote-board monitor for the tr-bot-v2 paper-trading bot — one dark lacquered surface ruled by hairlines, ivory tabular numerals, lamp state grammar.
colors:
  ground: "#0f1113"
  band: "#121518"
  band-alt: "#101315"
  flap-cell: "#191d21"
  rule: "#23282d"
  rule-strong: "#2f363c"
  ink: "#e8e4d8"
  ink-2: "#a5a196"
  ink-3: "#8a867c"
  lamp-ok: "#35c56e"
  lamp-warn: "#e5a50a"
  lamp-kill: "#e5484d"
typography:
  figure-hero:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "clamp(24px, 8.2vw, 34px)"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.01em"
  status-label:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "21px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.1em"
  ticker:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    letterSpacing: "0.12em"
  board-cap:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    letterSpacing: "0.2em"
  table-head:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.16em"
  flap-glyph:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "13px"
    fontWeight: 500
  body:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  label-mono:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 400
rounded:
  none: "0"
  flap: "3px"
  lamp: "50%"
spacing:
  xs: "4px"
  sm: "8px"
  row: "9px"
  md: "12px"
  gutter: "16px"
  band: "18px"
  tape-gap: "42px"
components:
  badge-paper:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    typography: "{typography.ticker}"
    padding: "0 12px"
  status-band:
    backgroundColor: "{colors.band}"
    textColor: "{colors.ink}"
    padding: "18px 16px 16px"
  lamp-ok:
    backgroundColor: "{colors.lamp-ok}"
    rounded: "{rounded.lamp}"
    size: "10px"
  lamp-kill:
    backgroundColor: "{colors.lamp-kill}"
    rounded: "{rounded.lamp}"
    size: "10px"
  lamp-event:
    backgroundColor: "{colors.lamp-ok}"
    rounded: "{rounded.lamp}"
    size: "7px"
  flap-cell:
    backgroundColor: "{colors.flap-cell}"
    textColor: "{colors.ink}"
    rounded: "{rounded.flap}"
    typography: "{typography.flap-glyph}"
    padding: "2px 4px"
  equity-figure:
    textColor: "{colors.ink}"
    typography: "{typography.figure-hero}"
  position-cell:
    textColor: "{colors.ink-2}"
    padding: "9px 16px"
  event-row:
    textColor: "{colors.ink}"
    padding: "9px 16px"
  demo-band:
    backgroundColor: "color-mix(in srgb, {colors.lamp-warn} 9%, {colors.ground})"
    textColor: "{colors.lamp-warn}"
    padding: "8px 16px"
---

# Design System: TR-BOT/2 Board

## Overview

**Creative North Star: "The Quote Board"**

The dashboard is one dark lacquered surface in the manner of an exchange quote board: every fact lives in a ruled row, every row obeys fixed columns, and nothing floats. There are no cards, no glass, no gradients-as-chrome, and no decorative chrome at all — the 1px hairline grid is the entire composition. The bot's state reads like a listing on the board, and when the bot goes quiet, the board says so in lamp grammar instead of going blank.

The world is a trading-terminal / system-monitor hybrid, built for one operator glancing for 15–60 seconds, usually at night on an iPhone. Density is high but calm: warm ivory ink on near-black steel, tabular monospaced numerals, condensed caps tickers, and exactly three chromatic voices — the lamps. Green means ok or up, amber means attention, red means kill. Color is never decoration; every colored pixel is a state.

Motion carries the split-flap spirit: status text and the board clock flip character-by-character, new tape entries clack in, the ticker tape rolls, and a kill lamp blinks. All of it stops under `prefers-reduced-motion`.

**Key Characteristics:**
- One continuous ruled surface; sections are bands separated by 1px hairlines, not stacked cards.
- Warm ivory (#e8e4d8) on lacquered near-black (#0f1113); three-step ink ladder for hierarchy.
- Lamp grammar: green ok/up, amber attention (warnings, demo, focus, selection), red kill (blinking).
- Every numeral in IBM Plex Mono with `font-variant-numeric: tabular-nums`; every label in tracked Barlow Condensed caps.
- The flap cascade is the signature interaction — digits roll and settle per character when state changes.
- Read-only: no buttons, no inputs, no settings; the only interactive behavior is scroll, tape hover-pause, and auto-refresh on focus.

## Colors

A lacquered near-black steel ground carrying warm ivory ink, ruled by two weights of steel hairline, with chroma reserved entirely for the three state lamps.

### Primary (State Lamps)
- **Board Green** (#35c56e): the ok lamp and every positive signal — LIVE status, up-deltas, up tape values, the weight-bar fill. The only color a healthy board shows.
- **Signal Amber** (#e5a50a): the attention register — warning lamps (NO RUNS, STALE, non-zero exit), the DEMO DATA banner (amber tint mixed 9% into ground), the `:focus-visible` ring (2px), and text selection (28% tint). Reserved by law for attention, never decoration.
- **Kill Red** (#e5484d): the kill state only — kill lamp (which blinks at 1.4s) and down-deltas/down tape values. Appears nowhere else.

### Neutral
- **Lacquered Ground** (#0f1113): the page, the board, html background, PWA `theme_color`/`background_color`. Every dark value is tuned against it.
- **Raised Band** (#121518): the status band — the one row the eye must land on first sits a hair above ground.
- **Sunken Band** (#101315): the ticker tape strip and the equity row — a hair below ground, so the hero figure sits in a shallow recess.
- **Flap Tile** (#191d21): flap-cell plates; the only clearly visible "tile" tone, raised by a hairline border and hinge line.
- **Steel Hairline** (#23282d): the default rule — section dividers, row rules, compartment dividers in the header, weight-bar track, flap-cell borders.
- **Bright Hairline** (#2f363c): the stronger rule — positions table-header underline and the 4px scrollbar thumb only.
- **Ivory Paint** (#e8e4d8): primary ink — figures, tickers, status labels, event names, the PAPER badge.
- **Dimmed Ivory** (#a5a196): secondary ink — mono values in the table, event details, tape labels, section headers, cents in the equity figure.
- **Etched Ivory** (#8a867c): tertiary ink — small caps, timestamps, notes, captions, the footer. Holds ≥4.5:1 contrast on ground, which is the floor for any small text.

### Named Rules
**The Amber Register Rule.** Amber is the attention register — warning lamps, the DEMO banner, focus, selection — and nothing else. It is never decoration, never a brand accent, never present on a healthy state. If amber is on screen, something needs looking at.

**The Two-Weight Hairline Rule.** All structure is 1px rules in exactly two weights: #23282d for everything, #2f363c where the grid must read stronger (table-header underline, scrollbar). Never thicker, never a different gray.

**The Ink Ladder Rule.** Three ivory steps only: full paint for what the board is saying, dimmed for supporting values, etched for captions. Small text may not go darker than #8a867c — that is the legibility floor, not a style preference.

## Typography

**Board Face:** Barlow Condensed (weights 500/600/700 via `next/font`), fallback "Arial Narrow", sans-serif.
**Digits Face:** IBM Plex Mono (weights 400/500/600 via `next/font`), fallback `ui-monospace, monospace`. Also the body default (14px / 1.45).

**Character:** a workhorse grotesque shouting the board's labels and a tabular monospace stating its numbers. The condensed face is always caps and always tracked; the mono face is always honest columns of digits.

### Hierarchy
- **Figure Hero** (Plex Mono 600, clamp(24px, 8.2vw, 34px), 42px at ≥1024px, line-height 1, −0.01em): the equity figure — the largest type on the board, cents dropped to Dimmed Ivory at weight 400.
- **Status Label** (Barlow Condensed 700, 21px, line-height 1.1, 0.1em): LIVE / STALE / KILL SWITCH — the flap-set state text in the status band.
- **Ticker** (Barlow Condensed 500, 13px, 0.12em): tape strip items, PAPER badge (700, 0.14em); values inside tape items flip to Plex Mono 500.
- **Board Cap** (Barlow Condensed 600, 12px, 0.2em): section headers (POSITIONS, THE TAPE), the EQUITY · USD caption; the aside variant steps down to 10px / 0.16em.
- **Table Head** (Barlow Condensed 600, 11px, 0.16em): column headers and the LAST CYCLE caption (11px, 0.18em variant).
- **Ticker Large** (Barlow Condensed 600, 14px, 0.1em): position tickers — NVDA, MSFT — the loudest condensed caps in the table.
- **Event Name** (Barlow Condensed 600, 12.5px, 0.14em): audit event names, underscore-spaced to caps.
- **Body** (Plex Mono 400, 14px, line-height 1.45): base text; the status note renders at 12px.
- **Label Mono** (Plex Mono 400, 10.5–12px): timestamps, counts, CASH line, event details (11.5px), footer. Etched or Dimmed Ivory only.
- **Flap Glyph** (Plex Mono 500, 13px; 16px in the large variant): digits inside flap cells, tabular.

### Named Rules
**The Two Voices Rule.** Barlow Condensed speaks labels; IBM Plex Mono speaks everything numeric or annotative — every digit, timestamp, price, and note. A numeral never renders in the condensed face; a tracked caps label never renders in mono.

**The Tabular Law.** Every numeral gets `font-variant-numeric: tabular-nums`. Columns of figures must align; the board is read in vertical scans.

**The Tracking Law.** Condensed caps are always tracked 0.1–0.2em (weight and tracking rise together with authority: 500/0.12em to whisper, 700/0.1–0.14em to declare). Mono is never tracked — the hero figure's −0.01em is its only exception.

## Layout

A single-column board, mobile-first at 390px. The `body` pads itself with `env(safe-area-inset-*)` on all sides (`viewport-fit: cover`, black-translucent status bar), and the board is a flex column at `min-height: 100dvh`, centered, `max-width: 520px`, fenced by left/right hairlines — on a desktop it widens to 780px and nothing else changes. The footer pins to the bottom with `margin-top: auto`, so the READ-ONLY line sits at the foot of the glass at every height.

The composition is a stack of ruled bands, each closed by a 1px bottom rule: header (min-height 52px, compartments divided by vertical hairlines — badge left, product mark, flap clock right), ticker tape, optional DEMO band, status band, equity row, positions, the tape log, footer. The universal horizontal gutter is 16px; ruled rows pad at 9px vertical; baseline-aligned section-header rows pad 12px top / 8px bottom.

Tables use fixed columns that never move: positions grid is `minmax(0, 1fr) 92px 64px` (SYMBOL / VALUE / WT% — qty is deferred to the position-sync phase by DB contract), widening to `1fr 140px 96px` at ≥1024px. Numeric columns are right-aligned and separated by 1px left hairlines; long text truncates with ellipsis rather than wrapping. The event log grid is `14px 62px minmax(0, 1fr)` with an 8px gap. The weight bar is a 72px track (180px max on desktop).

### Named Rules
**Columns Never Move.** Table columns are fixed widths; at wider viewports the grid widens, it never reflows, stacks, or hides columns.

**The Row Is the Header Rule.** Section headers are baseline-ruled rows inside the grid — condensed caps left, mono count right — not floating eyebrow badges or kickers above content. No kickers exist in this system.

**The Single Board Rule.** One surface, one scroll. No nested cards, no modals, no secondary panes; if a fact matters it gets a ruled row on the board.

## Elevation & Depth

The system is flat by doctrine: no card shadows, no glass, no gradients-as-chrome. Depth is conveyed by tonal banding and rules alone — ground #0f1113, sunken band #101315, raised band #121518, flap tile #191d21 — a four-step ladder of near-invisible shifts that reads as lacquer, plus the two-weight hairline grid doing all the structural work. Overlay depth is reserved for state: the kill lamp blinks, the flap tiles sit on their bordered plates with a hinge line, the DEMO band tints itself amber. `box-shadow` exists exactly once in the entire system.

### Shadow Vocabulary
- **Lamp Halo** (`box-shadow: 0 0 10px 1px color-mix(in srgb, var(--lamp-color) 45%, transparent)`): a single 10px glow around the status lamp, tinted by its own state color. The only shadow in the system; event-log lamps inherit the same formula at 7px.

### Named Rules
**The Only Glow Is a Live Lamp.** `box-shadow` appears only on the status lamp, as a halo of its own state color. Surfaces never cast shadows; nothing hovers above the board.

## Shapes

Square by law. The radius vocabulary contains exactly two entries: flap-cell tiles at 3px and lamps at 50% (10px status, 7px event-log). Every other corner — every band, row, cell, and the board itself — is square. Corners are not how this system communicates.

Lines and bars carry the form language: 1px hairlines in two weights, vertical compartment rules in the header, 1px left dividers on numeric columns, the 2px weight bar (Steel Hairline track, Board Green fill at 70% opacity), and the flap hinge — a 1px line of 85%-opaque ground across each flap cell's vertical center. Icons are authored inline SVG only, one stroke grammar: solid 8px triangles (up/down deltas) and solid 8px circles (the inline lamp dot), always `currentColor`, never unicode or emoji.

## Components

No buttons, inputs, or navigation exist — the surface is read-only by contract. The component set is the board's own furniture.

### Board Header
- **Shape:** flex row, min-height 52px, compartments divided by 1px vertical hairlines.
- **PAPER badge** (left): stamped box — Barlow Condensed 700 13px / 0.14em Ivory Paint, 12px horizontal padding, an 8px inline-SVG lamp dot in currentColor; always visible, always first.
- **Product mark** (center): TR-BOT/2 in Barlow Condensed 500 13px / 0.18em Etched Ivory, ellipses when cramped.
- **Board clock** (right): flap digits, HH:MM:SS UTC, inside a left-ruled compartment.

### Ticker Tape
- **Style:** a nowrap marquee strip on Sunken Band, ruled top and bottom; items are Ticker caps in Dimmed Ivory with Plex Mono values in Ivory Paint; gap 42px.
- **Motion:** rolls left at 36s linear infinite via a duplicated half-track (seamless loop); hover pauses it; `aria-hidden` (it is a restatement of on-board facts).
- **State color:** up values Board Green, down values Kill Red — lamp grammar extended to the tape.

### Status Band (the row the eye lands on)
- **Shape:** flex row on Raised Band, padding 18px 16px 16px, gap 10px.
- **Lamp:** 10px circle, halo glow, three states — ok (green), warn (amber), kill (red, blinking 1.4s `steps(2, start)` to 35% opacity).
- **State label:** Status Label type set in flap digits — LIVE / NO RUNS / STALE / EXIT n / KILL SWITCH, with a 12px mono note beneath (Etched Ivory).
- **Last cycle:** right-aligned caption (Table Head caps) over a flap-digit HH:MM time.

### Flap Digits (signature component)
- **Shape:** a row of per-character cells — Flap Tile background, 1px Steel Hairline border, 3px radius, 2px 4px padding, a 1px hinge line across the vertical center; glyphs are Plex Mono 500 13px tabular (16px large variant), 2px cell gap.
- **Behavior:** on any value change each cell rolls through random glyphs (45ms per step, bounded 4–7 steps) and settles on its target, staggered 60ms per character left-to-right. Accessible: container carries `aria-label`, cells are `aria-hidden`.
- **Reduced motion:** the cascade is skipped entirely (checked via `matchMedia`); static target text renders.

### Equity Row
- **Shape:** two-column grid (`1fr auto`) aligned to baseline-end on Sunken Band, 16px padding.
- **Figure:** the Figure Hero — dollars in Ivory Paint, cents in Dimmed Ivory 400; caption EQUITY · USD in Board Cap caps.
- **Aside:** SINCE START caption, delta with 8px triangle arrow (green up / red down), CASH line in Label Mono.

### Positions Table
- **Shape:** fixed-column grid (SYMBOL / VALUE / WT%); header row in Table Head caps on Etched Ivory, underlined with the Bright Hairline; data rows closed by Steel Hairlines, 9px 16px cells.
- **Cells:** tickers in Ticker Large caps (Ivory Paint) with a 72px 2px weight bar beneath (track Steel Hairline, fill Board Green 70% — width scaled ×6 so typical 5–17% weights read across the track); values in mono, the primary value at weight 500 Ivory Paint, secondary figures Dimmed Ivory; numerics right-aligned behind 1px left dividers.
- **Responsive:** columns widen at ≥1024px; rows never wrap, cells ellipsize.

### The Tape (event log)
- **Shape:** event rows ruled off at 9px 16px — a 7px state lamp, a mono HH:MM timestamp, then the event name (Event Name caps) with its detail line beneath (11.5px mono, Dimmed Ivory, ellipsis).
- **Lamp mapping:** event name carries the signal — /kill/ → red, /fail|error|reject|exit/ → amber, else green.
- **Motion:** new rows clack in — 0.34s `cubic-bezier(0.2, 0.9, 0.3, 1)`, 5px drop with 1.5px blur clearing, staggered 0.05–0.33s across the first five rows.

### Demo Band
- **Style:** an amber-attention strip — Signal Amber text (Barlow Condensed 600 12px / 0.14em) on a 9% amber tint of ground — declaring DEMO DATA — SET TURSO CREDENTIALS TO GO LIVE. Honesty rendered as a state, not a hidden fallback.

### Board Foot
- **Style:** pinned footer, 10.5px mono in Etched Ivory; READ-ONLY in Barlow Condensed 600 / 0.16em; data age and feed source ("demo" / "turso") on the right.

### Motion (system-wide)
- **Motion Grammar:** mechanical, stepped, never smooth-floaty — linear tape, stepped blink, settle-on-target flaps, one eased clack. All animation (tape roll, kill blink, row clack, flap cascade) is disabled under `prefers-reduced-motion`. Auto-refresh on focus/visibility re-renders the server component so flap digits re-cascade and ages stay honest.

## Do's and Don'ts

### Do:
- **Do** use the lamp grammar for every state: green #35c56e ok/up, amber #e5a50a attention, red #e5484d kill (blinking). A colored pixel is always a state.
- **Do** set every numeral in IBM Plex Mono with `font-variant-numeric: tabular-nums`, right-aligned in tables.
- **Do** set condensed caps tracked (0.1–0.2em) with weight matching authority (500 → 700).
- **Do** structure content as ruled rows: `border-bottom: 1px solid var(--rule)`, 16px gutters, 9px row padding.
- **Do** keep the focus ring as `2px solid var(--lamp-warn)` with 2px offset, and selection as the 28% amber tint.
- **Do** render staleness honestly — STALE with an amber lamp past 48h, kill blinks, ages shown as "2h ago" — never a blank or zero.
- **Do** honor `prefers-reduced-motion` for every animation, including the flap cascade.
- **Do** widen the grid on larger screens (520px → 780px at ≥1024px) instead of reflowing columns.

### Don't:
- **Don't** use cards, glass, gradients-as-chrome, or surface shadows — depth is tonal banding and hairlines; the lamp halo is the system's only `box-shadow`.
- **Don't** use amber as decoration or brand accent, and never on a healthy state; amber on screen means "look at this".
- **Don't** use red for anything but kill/down, or green for anything but ok/up.
- **Don't** add icon fonts, unicode glyphs, or emoji — icons are authored inline SVG in the one stroke grammar (8px solid triangles and dots, `currentColor`).
- **Don't** track mono digits, center numeric columns, or set a numeral in the condensed face.
- **Don't** let columns reflow or stack responsively; fixed columns widen, never move.
- **Don't** introduce a second accent hue, a lighter rule than 1px, or small text darker than #8a867c.
- **Don't** add write affordances — no buttons, inputs, or settings; the board states, the operator acts in the repo.
