#!/usr/bin/env bash
# Installs Lilliput on a Debian/Ubuntu VM or LXC as a dedicated, non-login user.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then echo "Run as root: sudo bash scripts/install-service.sh"; exit 1; fi
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$APP_DIR" == *' '* ]]; then echo 'App directory paths with spaces are unsupported; use /opt/lilliput.'; exit 1; fi
if [ ! -f "$APP_DIR/server.py" ]; then echo 'server.py not found.'; exit 1; fi
if ! id -u lilliput >/dev/null 2>&1; then useradd --system --home-dir /var/lib/lilliput --shell /usr/sbin/nologin lilliput; fi
install -d -m 0750 -o lilliput -g lilliput /var/lib/lilliput
# Preserve local-test data if present; do not overwrite existing service data.
if [ -f "$APP_DIR/data/lilliput.sqlite" ] && [ ! -f /var/lib/lilliput/lilliput.sqlite ]; then
  cp "$APP_DIR/data/lilliput.sqlite" /var/lib/lilliput/lilliput.sqlite
  chown lilliput:lilliput /var/lib/lilliput/lilliput.sqlite
fi
cat > /etc/systemd/system/lilliput.service <<EOF
[Unit]
Description=Lilliput - Real-time Tiny Town
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=lilliput
Group=lilliput
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
Environment=WORLD_DB=/var/lib/lilliput/lilliput.sqlite
Environment=HOST=0.0.0.0
Environment=PORT=8788
Environment=LILLIPUT_TIMEZONE=America/New_York
ExecStart=/usr/bin/python3 $APP_DIR/server.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=/var/lib/lilliput

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now lilliput
printf '\nLilliput service installed.\nStatus: systemctl status lilliput\nLogs: journalctl -u lilliput -f\nData: /var/lib/lilliput/lilliput.sqlite\nPort: 8788\n'
if [[ "$APP_DIR" == /root/* ]]; then echo 'WARNING: A service user may not read files in /root. Move this repo to /opt/lilliput and rerun.'; fi
