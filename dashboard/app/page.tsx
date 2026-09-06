import { FlapDigits } from "@/components/FlapDigits";
import { AutoRefresh } from "@/components/AutoRefresh";
import { ArrowDown, ArrowUp, LampDot } from "@/components/Arrow";
import { boardStatus, fmtAgo, getBoardData, type BoardData } from "@/lib/data";

export const dynamic = "force-dynamic";

function utcClock(d: BoardData): string {
  const t = new Date(d.fetchedAt);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(t.getUTCHours())}:${p(t.getUTCMinutes())}:${p(t.getUTCSeconds())}`;
}

function fmtMoney(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function fmtQty(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function lampFor(event: string): "ok" | "warn" | "kill" {
  if (/kill/i.test(event)) return "kill";
  if (/fail|error|reject|exit/i.test(event)) return "warn";
  return "ok";
}

function tapeItems(d: BoardData): { label: string; value: React.ReactNode }[] {
  const items: { label: string; value: React.ReactNode }[] = [];
  if (d.equity) {
    const pct = ((d.equity.current / d.equity.start - 1) * 100).toFixed(2);
    items.push({
      label: "EQUITY",
      value: <strong>${fmtMoney(d.equity.current)}</strong>,
    });
    items.push({
      label: "SINCE START",
      value: (
        <strong className={Number(pct) >= 0 ? "up" : "down"}>
          {Number(pct) >= 0 ? <ArrowUp /> : <ArrowDown />} {Math.abs(Number(pct)).toFixed(2)}%
        </strong>
      ),
    });
    items.push({
      label: "POSITIONS",
      value: <strong>{String(d.equity.positions.length)}</strong>,
    });
  }
  if (d.lastRun) {
    items.push({ label: "LAST CYCLE", value: <strong>{d.lastRun.status.toUpperCase()}</strong> });
    items.push({ label: "MODE", value: <strong>{d.lastRun.mode || "PAPER"}</strong> });
  }
  items.push({ label: "FEED", value: <strong>{d.demo ? "DEMO" : "TURSO"}</strong> });
  return items;
}

export default async function Board() {
  const d = await getBoardData();
  const st = boardStatus(d);
  const delta = d.equity ? d.equity.current / d.equity.start - 1 : 0;
  const deltaPct = (delta * 100).toFixed(2);
  const tape = tapeItems(d);
  const [equityWhole, equityCents] = d.equity
    ? d.equity.current.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).split(".")
    : ["—", "00"];

  return (
    <main className="board">
      <AutoRefresh />
      <header className="board-head">
        <span className="badge-paper">
          <LampDot />PAPER TRADING
        </span>
        <span className="head-mark">TR-BOT/2</span>
        <span className="head-clock">
          <FlapDigits value={utcClock(d)} />
        </span>
      </header>

      <div className="tape" aria-hidden="true">
        <div className="tape-track">
          {[0, 1].map((dup) => (
            <span key={dup} className="tape-copy">
              {tape.map((t, i) => (
                <span className="tape-item" key={i}>
                  {t.label}
                  {t.value}
                </span>
              ))}
            </span>
          ))}
        </div>
      </div>

      {d.demo && <div className="demo-band">DEMO DATA — SET TURSO CREDENTIALS TO GO LIVE</div>}

      <section className="status-band" aria-label="bot status">
        <span className={`lamp ${st.lamp}`} aria-hidden="true" />
        <div className="status-main">
          <div className="status-label">
            <FlapDigits value={st.label} />
          </div>
          <div className="status-note">{st.note}</div>
        </div>
        <div className="status-time">
          <span className="cap">LAST CYCLE</span>
          {d.lastRun ? (
            <FlapDigits
              value={new Date(d.lastRun.startedAt)
                .toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" })}
            />
          ) : (
            <FlapDigits value="--:--" />
          )}
        </div>
      </section>

      {d.equity && (
        <section className="equity-row" aria-label="portfolio equity">
          <div>
            <div className="equity-cap">EQUITY · USD</div>
            <div className="equity-figure">
              ${equityWhole}
              <span className="cents">.{equityCents}</span>
            </div>
          </div>
          <div className="equity-aside">
            <span className="equity-cap">SINCE START</span>
            <span className={`equity-delta ${delta >= 0 ? "up" : "down"}`}>
              {delta >= 0 ? <ArrowUp /> : <ArrowDown />} {Math.abs(Number(deltaPct)).toFixed(2)}%
            </span>
            <span className="equity-cash">CASH ${fmtMoney(d.equity.cash)}</span>
          </div>
        </section>
      )}

      {d.equity && d.equity.positions.length > 0 && (
        <section aria-label="positions">
          <div className="section-rule">
            <h2>POSITIONS</h2>
            <span className="count">{String(d.equity.positions.length).padStart(2, "0")}</span>
          </div>
          <div className="positions-grid cols3">
            <span className="h">SYMBOL</span>
            <span className="h">VALUE</span>
            <span className="h">WT%</span>
            {d.equity.positions.map((p) => (
              <span key={p.symbol} style={{ display: "contents" }}>
                <span className="c pos-ticker">
                  {p.symbol}
                  <span className="wt-bar" aria-hidden="true">
                    <span style={{ width: `${Math.min(100, p.weight * 100 * 6)}%` }} />
                  </span>
                </span>
                <span className="c pos-num strong">${fmtMoney(p.value)}</span>
                <span className="c pos-num">{(p.weight * 100).toFixed(1)}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {d.events.length > 0 && (
        <section aria-label="events">
          <div className="section-rule">
            <h2>THE TAPE</h2>
            <span className="count">LAST {String(Math.min(d.events.length, 12)).padStart(2, "0")}</span>
          </div>
          {d.events.map((e, i) => (
            <div className="event-row" key={`${e.ts}-${i}`}>
              <span className={`lamp ${lampFor(e.event)} ${e.event}`} aria-hidden="true" />
              <span className="event-time">
                {new Date(e.ts).toLocaleTimeString("en-GB", {
                  hour: "2-digit",
                  minute: "2-digit",
                  timeZone: "UTC",
                })}
              </span>
              <span style={{ minWidth: 0 }}>
                <span className="event-name">{e.event.replace(/_/g, " ").toUpperCase()}</span>
                <span className="event-detail">{e.detail}</span>
              </span>
            </div>
          ))}
        </section>
      )}

      <footer className="board-foot">
        <span className="ro">READ-ONLY</span>
        <span>
          data {fmtAgo(d.equity?.ts ?? d.lastRun?.startedAt ?? d.fetchedAt)} ·{" "}
          {d.demo ? "demo" : "turso"}
        </span>
      </footer>
    </main>
  );
}
