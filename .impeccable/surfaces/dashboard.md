# Surface brief — dashboard (tr-bot-v2)

Scope: the whole dashboard surface (single route, mobile-first PWA). Mode: **Operate**.
Audience: one operator; job: confirm the bot is alive and how it is doing in a 15–60s glance;
action: notice abnormal state (stale heartbeat, kill switch, failed cycle) and go fix it in the repo/VM;
proof/content: real Turso state (runs, equity_snapshots, audit_log) or a labeled DEMO dataset;
constraints: read-only, PAPER badge always visible, dark, iPhone safe-areas, no settings UI.

Chosen direction (unattended run: assignment taken per the skill's fallback, stated in report):
**THE QUOTE BOARD** — the exchange quote-board/ticker-tape ledger, modernized.
- Verdicts recorded: split-flap concourse COMPETITIVE (same row/lamp family; donates per-character
  flap cascade + amber-lamp state grammar); CRT-arcade DECLINED (donates palette law: urgent amber
  reserved strictly for warnings, never decoration); civic-bureau DECLINED (donates hairline-rule
  discipline: the ruled grid is the entire composition, columns never move).

## Direction contract

THESIS: The bot's state reads like a listing on an exchange board — one dark lacquered surface where
ruled rows and fixed columns carry every fact; it refuses the consumer-fintech card-stack and the
decorative-terminal neon.

OWN-WORLD: near-black lacquered ground (#101214 range), 1px steel hairlines ruling the entire
composition, ivory tabular numerals, caps tickers in a workhorse grotesque, digits in a monospace
tabular face; lamp states — green ok, amber warning (reserved by law for warnings only), red kill;
a paper-tape strip carries the event log; no cards, no glass, no gradients-as-chrome.

STORY: "The board is live, the bot traded, here is exactly what it did" — or, when stale, the board
says so in lamp grammar instead of going quiet.

FIRST VIEWPORT (390×844, code-led contract): (1) board header row: PAPER badge left (stamped-box),
UTC board clock right, product mark; (2) status band: heartbeat row — lamp + last-run time in flap
digits + cycle status, the row the eye lands on first; (3) equity hero row: large tabular equity
figure with since-start delta and cash, ruled beneath; (4) the positions table — caps ticker column,
qty, value, weight — ruled rows, fixed columns. Primary action surface: none (read-only); the tape
(scrolling event strip) sits at the foot and is the signature interaction carrier.

SIGNATURE INTERACTION: the flap cascade — status text and clock digits flip character-by-character
(spirit of the split-flap board) when state changes; new tape entries push in with a single clack.

FORM: assigned grounded candidate #4 (seed key 10580d2d). FINISH: unreviewed and undocumented is
unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster
carrying its provenance.

Unresolved: none blocking build; reviewer may re-open.

## Review adaptations (recorded)

- **QTY column deferred with citation** (finish review): `positions_json`
  carries symbol→market-value only (DB contract, docs/DB_SCHEMA.md); qty ships
  with the position-sync phase. Positions render SYMBOL/VALUE/WT% at every
  width; desktop widens the ruled grid instead.
- **SINCE START** spans the last 400 equity snapshots (dashboard window) —
  exact for the daily-cycle cadence; comment recorded in lib/data.ts.
