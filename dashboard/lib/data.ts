// Data layer: reads the bot's state from Turso (libSQL HTTP) or renders a
// labeled DEMO dataset when credentials are absent. Read-only by contract.

export type CycleStatus = "ok" | "planned" | "halted" | "failed" | "sync";

export interface BoardData {
  demo: boolean;
  fetchedAt: string; // ISO
  lastRun: {
    startedAt: string;
    status: CycleStatus;
    exitCode: number | null;
    mode: string;
  } | null;
  staleHours: number | null; // age of last run in hours
  equity: {
    ts: string;
    current: number;
    start: number; // first snapshot
    cash: number;
    positions: Position[];
  } | null;
  events: AuditEvent[];
  killActive: boolean;
}

export interface Position {
  symbol: string;
  value: number;
  weight: number;
}

export interface AuditEvent {
  ts: string;
  event: string;
  detail: string;
}

const STALE_HOURS = 49;

// --- Turso pipeline client (mirror of src/trbot/state_turso.py) --------------

interface PipelineResult {
  cols: { name: string }[];
  rows: { type: string; value: unknown }[][];
}

async function tursoQuery<T>(
  url: string,
  token: string,
  sql: string,
): Promise<T[]> {
  const host = url.startsWith("libsql://")
    ? `https://${new URL(url.replace("libsql://", "https://")).hostname}`
    : url.replace(/\/$/, "");
  const res = await fetch(`${host}/v2/pipeline`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      requests: [
        { type: "execute", stmt: { sql } },
        { type: "close", stmt: null },
      ],
    }),
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`turso HTTP ${res.status}`);
  const payload = (await res.json()) as { results?: { type: string; response?: { result?: PipelineResult } }[] };
  const first = payload.results?.[0];
  if (!first || first.type === "error") throw new Error("turso query error");
  const result = first.response?.result;
  if (!result) return [];
  return result.rows.map((row) => {
    const obj: Record<string, unknown> = {};
    result.cols.forEach((c, i) => {
      const v = row[i];
      obj[c.name] = v?.type === "integer" ? Number(v.value) : v?.type === "float" ? Number(v.value) : v?.type === "null" ? null : v?.value;
    });
    return obj as T;
  });
}

// --- board assembly -----------------------------------------------------------

function parsePositions(posJson: string | null): Position[] {
  if (!posJson) return [];
  try {
    const raw = JSON.parse(posJson) as Record<string, number>;
    const total = Object.values(raw).reduce((a, b) => a + b, 0);
    return Object.entries(raw)
      .map(([symbol, value]) => ({ symbol, value, weight: total > 0 ? value / total : 0 }))
      .sort((a, b) => b.value - a.value);
  } catch {
    return [];
  }
}

function assemble({ run, snaps, events, kill }: {
  run: Record<string, unknown> | undefined;
  snaps: Record<string, unknown>[];
  events: Record<string, unknown>[];
  kill: Record<string, unknown> | undefined;
}): BoardData {
  const lastSnap = snaps.at(-1);
  const firstSnap = snaps[0];
  const startedAt = run?.started_at ? String(run.started_at) : "";
  const ageH = startedAt
    ? (Date.now() - new Date(startedAt).getTime()) / 3_600_000
    : null;
  const equityNow = lastSnap ? Number(lastSnap.equity) : null;
  const equityStart = firstSnap ? Number(firstSnap.equity) : null;
  const killDetail = kill ? String(kill.detail ?? "") : "";
  return {
    demo: false,
    fetchedAt: new Date().toISOString(),
    lastRun: run
      ? {
          startedAt,
          status: String(run.status ?? "failed") as CycleStatus,
          exitCode: run.exit_code === null || run.exit_code === undefined ? null : Number(run.exit_code),
          mode: String(run.mode ?? ""),
        }
      : null,
    staleHours: ageH,
    equity:
      equityNow !== null
        ? {
            ts: String(lastSnap!.ts),
            current: equityNow,
            start: equityStart ?? equityNow,
            cash: Number(lastSnap!.cash ?? 0),
            positions: parsePositions(lastSnap!.positions_json as string),
          }
        : null,
    events: events.map((e) => ({
      ts: String(e.ts),
      event: String(e.event),
      detail: String(e.detail ?? ""),
    })),
    killActive: /kill/i.test(killDetail) ? true : false,
  };
}

export async function getBoardData(): Promise<BoardData> {
  const url = process.env.TURSO_DATABASE_URL;
  const token = process.env.TURSO_AUTH_TOKEN;
  if (!url || !token) return demoData();
  try {
    const [runs, snaps, events, kill] = await Promise.all([
      tursoQuery<Record<string, unknown>>(url, token,
        "SELECT started_at, status, exit_code, mode FROM runs ORDER BY run_id DESC LIMIT 1"),
      tursoQuery<Record<string, unknown>>(url, token,
        "SELECT ts, equity, cash, positions_json FROM equity_snapshots ORDER BY ts DESC LIMIT 400"),
      tursoQuery<Record<string, unknown>>(url, token,
        "SELECT ts, event, detail FROM audit_log ORDER BY id DESC LIMIT 12"),
      tursoQuery<Record<string, unknown>>(url, token,
        "SELECT ts, event, detail FROM audit_log WHERE event LIKE '%kill%' ORDER BY id DESC LIMIT 1"),
    ]);
    return assemble({
      run: runs[0],
      snaps: snaps.reverse(),
      events,
      kill: kill[0],
    });
  } catch {
    return { ...demoData(), demo: true };
  }
}

// --- DEMO dataset (labeled as such in the UI; used when credentials absent) ---

export function demoData(): BoardData {
  const now = Date.now();
  const iso = (ms: number) => new Date(ms).toISOString();
  let equity = 100_000;
  const snaps = Array.from({ length: 180 }, (_, i) => {
    equity *= 1 + Math.sin(i / 9) * 0.004 + (i > 150 ? 0.0035 : 0.0018);
    const positions: Record<string, number> = {};
    const names = ["NVDA", "MSFT", "XOM", "UNH", "JPM", "COST", "LLY", "WMT", "CVX", "AAPL"];
    const weights = [0.16, 0.14, 0.12, 0.11, 0.10, 0.09, 0.08, 0.08, 0.07, 0.05];
    names.forEach((n, k) => (positions[n] = equity * weights[k]));
    return {
      ts: iso(now - (180 - i) * 86_400_000),
      equity,
      cash: equity * 0.02,
      positions_json: JSON.stringify(positions),
    };
  });
  return {
    demo: true,
    fetchedAt: iso(now),
    lastRun: {
      startedAt: iso(now - 3_600_000 * 2.2),
      status: "ok",
      exitCode: 0,
      mode: "PAPER",
    },
    staleHours: 2.2,
    equity: {
      ts: snaps.at(-1)!.ts,
      current: equity,
      start: 100_000,
      cash: equity * 0.02,
      positions: parsePositions(snaps.at(-1)!.positions_json),
    },
    events: [
      { ts: iso(now - 3_600_000 * 2.2), event: "cycle_finish", detail: "ok exit=0 submitted 3 orders" },
      { ts: iso(now - 3_600_000 * 2.3), event: "order_submitted", detail: "AAPL buy qty=41.2" },
      { ts: iso(now - 3_600_000 * 2.3), event: "risk_decision", detail: "[APPROVED] approved 10 positions, gross 0.980" },
      { ts: iso(now - 3_600_000 * 26), event: "kill_switch", detail: "drawdown -10.4% breached -10% threshold" },
      { ts: iso(now - 3_600_000 * 26 + 5_400_000), event: "cooldown_expired", detail: "trading resumed, HWM reset" },
    ],
    killActive: false,
  };
}

export function boardStatus(d: BoardData): {
  lamp: "ok" | "warn" | "kill";
  label: string;
  note: string;
} {
  if (d.killActive) return { lamp: "kill", label: "KILL SWITCH", note: "trading halted — reset on VM" };
  if (d.lastRun === null) return { lamp: "warn", label: "NO RUNS", note: "bot has never written state" };
  if ((d.staleHours ?? 0) > STALE_HOURS)
    return { lamp: "warn", label: "STALE", note: `last cycle ${Math.round(d.staleHours!)}h ago` };
  if (d.lastRun.exitCode !== null && d.lastRun.exitCode !== 0)
    return { lamp: "warn", label: `EXIT ${d.lastRun.exitCode}`, note: "cycle failed — check events" };
  return { lamp: "ok", label: "LIVE", note: `cycle ${d.lastRun.status} · ${fmtAgo(d.lastRun.startedAt)}` };
}

export function fmtAgo(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
  if (mins < 60) return `${mins}m ago`;
  const h = Math.round(mins / 60);
  if (h < 48) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}
