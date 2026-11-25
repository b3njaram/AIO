#!/usr/bin/env bash
set -euo pipefail
umask 077
BASE="$HOME/.local/share/jobbi-business"
PIN=7cf8b54f13eac82816e3363363ed7ae43e84dc28
mkdir -p "$BASE"
DEST="$BASE/dealcompare"
if [[ ! -d "$DEST/.git" ]]; then
  git clone git@github.com:b3njaram/dealcompare-local.git "$DEST"
fi
[[ -z "$(git -C "$DEST" status --porcelain --untracked-files=no)" ]] || { echo "Existing checkout modified; inspect before updating"; exit 1; }
git -C "$DEST" fetch origin "$PIN"
git -C "$DEST" checkout --detach "$PIN"
python3 -m venv "$BASE/sourcing-venv"
"$BASE/sourcing-venv/bin/python" -m pip install 'requests>=2.32,<3' 'beautifulsoup4>=4.12,<5'
echo "Ready: $BASE/sourcing-venv/bin/python"
