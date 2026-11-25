#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[[ "$ROOT" =~ ^/[a-zA-Z0-9_./-]+$ ]] || { echo 'Use a repository path without spaces'; exit 1; }
bash "$ROOT/business/dashboard/start.sh" --init
umask 077
mkdir -p "$HOME/.config/systemd/user"
UNIT="$HOME/.config/systemd/user/jobbi-business.service"
if [[ -e "$UNIT" ]]; then echo 'Existing service file retained; inspect it before changing'; else
cat > "$UNIT" <<EOF
[Unit]
Description=JobbiSoft private business dashboard
[Service]
Type=simple
WorkingDirectory=$ROOT
ExecStart=/bin/bash $ROOT/business/dashboard/start.sh
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
[Install]
WantedBy=default.target
EOF
fi
systemctl --user daemon-reload
systemctl --user enable --now jobbi-business
