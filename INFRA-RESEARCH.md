# Infrastructure Research — free-tier options for an always-on trading bot

**Researched:** 2026-09-06 (sources verified via web search; links inline)

---

## 1. Hosting

### Oracle Cloud Always Free — SELECTED
- Always Free resources have no time limit; include ARM Ampere A1 compute, 2 AMD micro VMs (1/8 OCPU, 1 GB each), 200 GB block storage, 10 TB/mo outbound transfer, free 10-Mbps flexible LB.
- **June 2026 change:** Always Free A1 allocation halved from 4 OCPU / 24 GB to **2 OCPU / 12 GB** (1,500 OCPU-hrs + 9,000 GB-hrs / month). Existing over-limit accounts had to reduce usage by Aug 18, 2026. Sources: [InfoQ](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/), [terminalbytes](https://terminalbytes.com), community threads.
- **Idle reclamation is enforced**: "Idle Always Free compute instances may be reclaimed by Oracle" ([official docs](https://docs.oracle.com/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)). Real-world report of a quiet instance terminated after ~1 week ([r/oraclecloud](https://www.reddit.com/r/oraclecloud/comments/1ulme2e/my_always_free_oracle_instance_got_idlereclaimed/)). Reclamation targets Always-Free-only accounts; **Pay-As-You-Go accounts are exempt** and get far better capacity access ([Oracle community notice](https://community.oracle.com/customerconnect/discussion/671904/reclamation-of-idle-compute-instances), [thread](https://www.reddit.com/r/oraclecloud/comments/1r3s5eu/which_region_to_go_for_free_tier_capacity/)).
- **Home region is locked at signup** — Always Free resources provision only in the home region ([seenlyst guide](https://www.seenlyst.com/blog/oracle-cloud-free-vps-out-of-capacity/)). US metros report chronic A1 "out of capacity."
- Capacity workaround: [hitrov/oci-arm-host-capacity](https://github.com/hitrov/oci-arm-host-capacity) retry script; try off-peak hours / different ADs.
- Community validation for this exact use case: [Trading Bot on Oracle Cloud](https://curvedtrading.com/articles/en/how/trading-bot-oracle-cloud/) — systemd service + timers, SSH keys, env-var secrets, minimal open ports. (Also an honest warning: hosting is the easy part; strategy edge is the hard part.)

### Rejected hosting alternatives
| Platform | Free tier reality (2026) | Why rejected |
|---|---|---|
| Render | Free web service spins down after 15 min idle; 750 instance-hrs/workspace/mo; **2026: bandwidth cut to 5 GB, free Postgres expires after 30 days** ([docs](https://render.com/docs/free), [comparison](https://www.codecapsules.io/blog/best-render-alternatives-in-2026-where-to-go-when-render-falls-short/)) | No always-on; v1 already suffered free-KV in-memory state loss |
| Fly.io | Pay-as-you-go, no true always-free VM | Cost risk |
| GitHub Actions as runner | Schedules best-effort: 20–40 min delays common (worst at top of hour), multi-hour drift documented; 2,000 min/mo private repos; schedules disabled after 60 days repo inactivity ([discussion 1](https://github.com/orgs/community/discussions/156282), [discussion 2](https://github.com/orgs/community/discussions/201738), [quota](https://github.com/orgs/community/discussions/202602)) | Keep for CI + emergency fallback runner only |
| Vercel/CF Workers (compute for bot) | Serverless, no persistent process | Wrong tool for a stateful bot |

## 2. Paper trading + market data

- **Alpaca paper trading**: free for all users, simulated fills against real quotes ([docs](https://docs.alpaca.markets/us/docs/paper-trading)). Account `PA30HK6GKPDP` already active ($100k, zero orders).
- **Free data = IEX feed only**: real-time, **200 req/min, 25 symbols/request**; IEX is ~2–3% of consolidated volume — fine for daily bars/signals; paper fills don't depend on our feed ([Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq), [forum](https://forum.alpaca.markets/t/iex-or-sip-with-a-free-account/17141)).
- **Fallback chain**: Massive (Polygon.io [rebranded Oct 30, 2025](https://massive.com/blog/polygon-is-now-massive/)) free tier = 5 req/min, 2 years EOD history ([pricing](https://massive.com/pricing)); Finnhub ~60 req/min free; Twelve Data ~800/day. Avoid: Stooq (JS proof-of-work bot protection, broke during v1), yfinance as primary (unofficial scraper, 429-prone after a few hundred tickers — [analysis](https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01)).
- **Crypto (later)**: Binance public REST is free/keyless for market data; Binance testnet for paper trading; CCXT as the client.

## 3. State database

| Option | Free tier | Verdict |
|---|---|---|
| **Turso (libSQL)** ✅ | ~100 DBs, 5 GB storage, 500M row reads, 10M row writes / mo ([turso.tech](https://turso.tech/)) | Selected. SQLite dialect = same as VM local mirror; CLI-first; no pause |
| Neon | 0.5 GB Postgres, scale-to-zero, no pause | Runner-up if Postgres preferred |
| Supabase | 500 MB, 2 projects, **paused after 7 days of no DB activity (manual restore)** ([pricing](https://supabase.com/pricing)) | Ruled out — a dead bot would pause the dashboard's DB |
| Render KV | Free tier in-memory only | Ruled out — v1's documented state-durability hole |

## 4. Dashboard hosting

- **Vercel Hobby**: $0, no card; 100 GB bandwidth/mo, 1M edge requests, 1M function invocations, 4 hrs active CPU; **non-commercial personal use allowed**; hard caps (no overage billing) ([docs](https://vercel.com/docs/plans/hobby), [limits](https://vercel.com/docs/limits)). Proposed stack: Next.js + shadcn/ui + Recharts / TradingView Lightweight Charts; reads Turso server-side with read-only token; polling/SSE for live-ness; honest "heartbeat stale" banner.
- Cloudflare Pages/Workers free: equally viable alternative (100k function requests/day).

## 5. Operations glue

- **Telegram bot** (BotFather): free trade fills / risk events / daily summary alerts.
- **Healthchecks.io** free tier: dead-man pings after each bot cycle; silence → email. Primary detection for VM death/reclamation.
- **UptimeRobot** free (50 monitors, 5-min): watch dashboard URL.
- **CI/CD**: private GitHub repo; Actions = lint/test/secret-audit; deploy via Actions-SSH or VM-side `git pull` timer.

## 6. Key numbers to remember

- Alpaca data: 200 req/min, 25 symbols/req (IEX free tier).
- Massive free: 5 req/min (space calls ~12 s apart), 2y history.
- Turso free: 10M writes/mo ≈ 230 writes/min sustained — orders of magnitude above our needs.
- Oracle free VM: 2 OCPU ARM / 12 GB RAM — a Python cycle uses ~1 core-sec per run.
- GH Actions private repo: 2,000 min/mo = ~66 min/day — enough for CI and *not* for bot cycles.
