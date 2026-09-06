#!/usr/bin/env bash
# tr-bot-v2 VM bootstrap — idempotent. Run as root on a fresh Ubuntu 24.04 ARM
# instance:  curl -fsSL https://raw.githubusercontent.com/dvrsh13/tr-bot-v2/main/deploy/bootstrap.sh | bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/dvrsh13/tr-bot-v2.git}"
REPO_DIR="/opt/trbot"
BOT_USER="trbot"

if [[ $EUID -ne 0 ]]; then echo "run as root (sudo)"; exit 1; fi

echo "== 1/7 unprivileged bot user =="
id -u "$BOT_USER" &>/dev/null || useradd -m -s /bin/bash "$BOT_USER"

echo "== 2/7 firewall: ssh in, everything else outbound-only =="
apt-get update -qq && apt-get install -y -qq ufw unattended-upgrades >/dev/null
ufw default deny incoming && ufw default allow outgoing
ufw allow OpenSSH && ufw --force enable

echo "== 3/7 automatic security updates =="
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

echo "== 4/7 uv + Python 3.12 (for the bot user) =="
sudo -iu "$BOT_USER" bash -s <<'UV'
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV

echo "== 5/7 clone + install framework =="
if [[ -d $REPO_DIR/.git ]]; then
  git -C "$REPO_DIR" fetch --all && git -C "$REPO_DIR" reset --hard origin/main
else
  git clone "$REPO_URL" "$REPO_DIR"
fi
chown -R "$BOT_USER":"$BOT_USER" "$REPO_DIR"
sudo -iu "$BOT_USER" bash -s <<PY
cd $REPO_DIR
~/.local/bin/uv sync --frozen
~/.local/bin/uv run pytest tests/ -q   # prove the install before it trades
PY

echo "== 6/7 systemd user units + lingering =="
install -o "$BOT_USER" -g "$BOT_USER" -m 644 "$REPO_DIR/deploy/systemd/trbot-paper.service" \
  "/home/$BOT_USER/.config/systemd/user/trbot-paper.service"
install -o "$BOT_USER" -g "$BOT_USER" -m 644 "$REPO_DIR/deploy/systemd/trbot-paper.timer" \
  "/home/$BOT_USER/.config/systemd/user/trbot-paper.timer"
loginctl enable-linger "$BOT_USER"

echo "== 7/7 env file scaffold =="
ENV_FILE="/home/$BOT_USER/.env"
if [[ ! -f $ENV_FILE ]]; then
  install -o "$BOT_USER" -g "$BOT_USER" -m 600 "$REPO_DIR/.env.example" "$ENV_FILE"
  echo ">> EDIT $ENV_FILE: paste ALPACA + TURSO credentials, then:"
  echo ">>   sudo -iu $BOT_USER  &&  systemctl --user enable --now trbot-paper.timer"
else
  echo ">> existing $ENV_FILE left untouched"
fi

echo "== bootstrap complete. Next: edit /home/$BOT_USER/.env, then enable the timer. =="
