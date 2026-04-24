#!/bin/bash
set -e
echo "🔧 Keenetic SSH — установка Telegram-бота"
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv sshpass

python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

[ ! -f .env ] && cp .env.example .env && echo "⚠️  Заполни .env (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)"

SVC="/etc/systemd/system/keenetic-ssh.service"
cat > "$SVC" <<EOF
[Unit]
Description=Keenetic SSH Telegram Bot
After=network.target

[Service]
WorkingDirectory=$DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$DIR/.venv/bin/python -m keenetic_ssh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable keenetic-ssh
systemctl restart keenetic-ssh
echo "✅ Сервис keenetic-ssh запущен. Лог: journalctl -u keenetic-ssh -f"
