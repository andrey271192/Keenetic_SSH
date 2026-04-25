#!/bin/bash
set -e
echo "Удаление Keenetic SSH…"
systemctl stop keenetic-ssh 2>/dev/null || true
systemctl disable keenetic-ssh 2>/dev/null || true
rm -f /etc/systemd/system/keenetic-ssh.service
systemctl daemon-reload 2>/dev/null || true
rm -rf /opt/keenetic-ssh
echo "Готово."
