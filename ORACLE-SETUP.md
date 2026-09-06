# Oracle Cloud setup guide — from failed signup to running bot

Step-by-step for the one piece that can't be automated from here: getting the
Oracle account live and the VM provisioned. Everything AFTER step 4 is
copy-paste or fully automated by the files in this repo.

---

## 1. Get the signup through

Common reasons signup fails, in observed order:

1. **Card verification rejects.** Oracle requires a credit/debit card for
   identity verification ($0–1 refundable hold). Prepaid cards and some virtual
   cards fail — use a real card. If the hold posts but signup fails anyway,
   wait 24h (holds drop) and retry; do NOT retry 5× in one day, the fraud
   system escalates.
2. **Name/address mismatch** with the card's billing record — match them
   exactly, including postal code.
3. **Email**: use an address never used with Oracle before (a fresh alias is
   fine); some domains (disposable-mail providers) are blocked outright.
4. **"Something went wrong" at the last step with no error code**: try a
   different browser, no ad-blockers, and if that fails, a different network
   (phone hotspot) — IP reputation matters.
5. If it keeps failing: open a support request via the "contact us" link on the
   signup error page — Oracle does resolve signup failures by email within
   1–3 days.

**Home region — the one permanent decision.** Always-Free resources can only be
provisioned in your **home region**, which can never be changed. Pick a
less-congested region near you. For India: `ap-mumbai-1` is the most contended
(and often out of ARM capacity); `ap-hyderabad-1` and `ap-bangalore-1` are
usually easier. US/EU metros are the most contested globally.

## 2. Immediately after first login

1. **Upgrade to Pay-As-You-Go** (optional but strongly recommended — costs $0
   while you only use Always-Free resources): Console → "Upgrade to Pay As You
   Go". Benefits: no idle-instance reclamation, far better ARM capacity
   access. The card is charged only for resources beyond the free allotment.
2. Create a **compartment** `trbot` (Identity → Compartments) — keeps billing
   and permissions clean.
3. Note your region identifier (top bar, e.g. `ap-hyderabad-1`) — you'll need
   it for the CLI.

## 3. Provision the VM (Console, one-time)

Compute → Instances → Create Instance:

| Setting | Value |
|---|---|
| Name | `trbot-vm` |
| Image | **Ubuntu 24.04** (canonical image) |
| Shape | `VM.Standard.A1.Flex` (Ampere ARM) |
| OCPU / RAM | **2 OCPU / 12 GB** (the 2026 Always-Free ARM allotment) |
| Networking | new VCN (default is fine); **Assign a public IPv4 address: yes** |
| SSH keys | paste your public key (`cat ~/.ssh/id_ed25519.pub`) — or let Oracle generate and download |

If you hit **"Out of capacity"**: try each availability domain (AD-1/2/3),
off-peak hours (early morning IST), and re-try over a few days. The community
script [hitrov/oci-arm-host-capacity](https://github.com/hitrov/oci-arm-host-capacity)
automates the retry via API. PAYG accounts rarely see this error.

Network Security: the default VCN security list allows port 22 only — that is
exactly what the bot needs (everything else is outbound).

## 4. Connect and run the bootstrap

```bash
ssh ubuntu@<PUBLIC_IP>
```

Then run the repo's cloud-init-equivalent bootstrap (idempotent — safe to
re-run):

```bash
# on the VM:
curl -fsSL https://raw.githubusercontent.com/dvrsh13/tr-bot-v2/main/deploy/bootstrap.sh | bash
```

What it does (also documented in `deploy/bootstrap.sh`, which you can read
before piping to bash): creates an unprivileged `trbot` user, installs uv +
Python 3.12 (ARM), clones the repo, installs the framework, installs the
systemd units (`deploy/systemd/*`), enables the firewall (22 in, everything
else out-only), sets up unattended security updates, and creates
`/home/trbot/.env` from `.env.example` for your secrets.

**Secrets — do this by hand after bootstrap** (never in the repo, never in
chat):

```bash
sudo -iu trbot
nano ~/.env   # paste ALPACA_KEY_ID / ALPACA_SECRET_KEY / TURSO_* values
chmod 600 ~/.env
```

## 5. Turn the bot on

```bash
sudo -iu trbot
systemctl --user daemon-reload        # units are user units under trbot
systemctl --user enable --now trbot-paper.timer   # daily cycle (market-aware)
systemctl --user status trbot-paper   # verify
journalctl --user -u trbot-paper -f   # watch the first cycle
```

First runs are **read-only plans** (order gates closed). Watch a few cycles,
then when YOU decide to go live with paper orders, open both gates:

```bash
# in ~/.env add:  TRBOT_ORDERS_ENABLED=true
# and in the repo config used on the VM: orders.enabled: true
systemctl --user restart trbot-paper.timer
```

## 6. Wire the state to Turso (so the dashboard is live)

1. Create the DB (from your Mac, one time):
   `turso db create trbot-v2 && turso db show trbot-v2 --url`
   `turso db tokens create trbot-v2` (read-write token for the VM;
   create a SECOND read-only token for the dashboard/Vercel:
   `turso db tokens create trbot-v2 --read-only`)
2. Put the URL + read-write token into the VM's `~/.env`.
3. `trbot sync-state` backfills local history; the runner writes to both from
   then on (dual-write).
4. Verify: open the dashboard → the DEMO band disappears.

## 7. Deploy the dashboard to Vercel

```bash
cd dashboard
npx vercel login              # once
npx vercel link               # link to a new project
npx vercel env add TURSO_DATABASE_URL    # paste libsql://... URL
npx vercel env add TURSO_AUTH_TOKEN      # paste the READ-ONLY token
npx vercel --prod
```

Or enable the repo's `dashboard-deploy.yml` GitHub Action by adding the
`VERCEL_TOKEN`/`VERCEL_ORG_ID`/`VERCEL_PROJECT_ID` secrets — it deploys on
every push that touches `dashboard/`. On the iPhone: open the URL in Safari →
Share → **Add to Home Screen** → it installs as a standalone PWA.

## 8. Monitoring (no extra service)

`heartbeat-monitor.yml` (already in the repo) runs on GitHub Actions twice an
hour: reads the last run from Turso using repo secrets
(`TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` — read-only token is enough) and
opens/updates a GitHub issue **"🚨 Bot heartbeat stale"** if the bot has been
silent > 49h. Silence = VM dead, timer dead, or Turso unreachable. That's the
dead-man switch — no third-party account needed.

## 9. Disaster playbook

- **VM dies / reclaimed:** state is in Turso; nothing is lost but compute.
  Re-provision = step 3 + step 4 (10 minutes), secrets re-paste.
- **Kill switch tripped:** it halts everything and pages you via the dashboard
  (red lamp) + GitHub issue. Inspect `journalctl --user -u trbot-paper`, fix
  the cause, then reset manually on the VM
  (`python -c "from trbot.risk import KillSwitch; KillSwitch(path='state/kill_switch.json').reset(confirm=True)"`)
  — the dashboard can never reset it.
- **Oracle region permanently out of capacity:** the framework runs identically
  on any ARM/AMD VPS, or as a stopgap on GitHub Actions (workflow_dispatch the
  paper runner) — but prefer Oracle.
