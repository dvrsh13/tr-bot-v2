# ISOLATION.md — environment isolation & disposal contract

tr-bot-v2 is built to be **fully disposable** during development. Nothing is
installed outside the project except the two pre-existing user-level tools
noted below. After development/deployment ends, follow §3 to remove everything.

## 1. What exists on this machine because of this project

| Artifact | Location | Remove with |
|---|---|---|
| Python venv (ALL deps: pandas, numpy, scipy, pydantic, yfinance, pytest, ruff, …) | `tr-bot-v2/.venv/` | `rm -rf .venv` (or delete the project folder) |
| uv lock + project metadata | `pyproject.toml`, `uv.lock`, `.python-version` | delete with project |
| Cached market data (34 parquet snapshots) | `tr-bot-v2/data/cache/` | delete with project (gitignored) |
| Trial ledger, local state DB | `tr-bot-v2/state/` | delete with project (gitignored) |
| Backtest plots / reports | `tr-bot-v2/reports/` | delete with project (gitignored) |
| Local git history | `tr-bot-v2/.git/` | delete with project |
| agent-reach research sandbox (from the planning session) | `~/agentreach-sandbox/` (~101 MB: uv venv + npm prefix, wrote nothing outside itself) | `rm -rf ~/agentreach-sandbox` |

Pre-existing (NOT created by this project, shared tooling):

| Artifact | Location | Note |
|---|---|---|
| `uv` binary + uv-managed CPython 3.12 | `~/.local/bin/uv`, uv's python store | was already installed; used to create `.venv`. Remove only if you no longer want uv at all: `rm -rf ~/.local/bin/uv ~/.local/share/uv` |
| Homebrew / node | `/opt/homebrew` | pre-existing system tooling, untouched |

## 2. Isolation guarantees held during the build

- **No global pip/npm installs.** Every dependency lives in `.venv/` (`uv sync` recreates it exactly from `uv.lock`).
- **No network services touched** during the overnight build (no new accounts, MCPs, or plugins). The only external calls were read-only: Yahoo Finance bar downloads (research snapshot) and OpenAlex/Semantic Scholar metadata (paper verification).
- **No secrets on disk.** The Alpaca adapter reads `ALPACA_KEY_ID` / `ALPACA_SECRET_KEY` from the environment at runtime; `.env*` and `*.key` are gitignored. Order submission is double-gated (config AND `TRBOT_ORDERS_ENABLED`).
- **No processes left running** — no daemons, launchd agents, or cron entries were created.
- **Paper-only by code:** the broker URL allowlist contains exactly the two Alpaca *paper* hosts; any live/prod URL fails config load (tested adversarially).

## 3. Full disposal (when the project ends)

```bash
rm -rf ~/Documents/tr-bot-v2          # project + venv + data + git history
rm -rf ~/agentreach-sandbox           # agent-reach research CLI sandbox
# optional, only if uv is no longer wanted:
# rm -rf ~/.local/bin/uv ~/.local/share/uv ~/.config/uv
```

That returns the machine to its pre-project state (plus nothing).
