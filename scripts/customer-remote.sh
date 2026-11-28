#!/usr/bin/env bash
# Official signed Tailscale packages. Does NOT enroll a device or configure routes.
set -euo pipefail
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && "$(uname -m)" == x86_64 ]] || { echo 'Dedicated Ubuntu 24.04 x86-64 only'; exit 1; }
[[ $EUID == 0 ]] || { echo 'Run as root only on the dedicated customer appliance'; exit 1; }
if command -v tailscale >/dev/null; then echo 'Existing Tailscale installation retained'; exit 0; fi
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg -o "$tmp/key"
curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list -o "$tmp/list"
# Accept only the expected official repository and signed-by scope.
grep -Fxq 'deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/ubuntu noble main' "$tmp/list"
if grep -Ev '^[[:space:]]*(#.*)?$|^deb \[signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg\] https://pkgs.tailscale.com/stable/ubuntu noble main$' "$tmp/list" | grep -q .; then echo 'Unexpected repository data'; exit 1; fi
for item in key list; do
  if [[ "$item" == key ]]; then dest=/usr/share/keyrings/tailscale-archive-keyring.gpg; else dest=/etc/apt/sources.list.d/tailscale.list; fi
  if [[ -L "$dest" ]] || { [[ -e "$dest" ]] && ! cmp -s "$tmp/$item" "$dest"; }; then echo "Existing repository config differs: $dest"; exit 1; fi
  install -m 0644 "$tmp/$item" "$dest"
done
apt-get update
apt-get --yes --no-remove install tailscale
systemctl enable --now tailscaled
echo 'Tailscale installed, NOT enrolled. Customer signs in to their own account via sudo tailscale up.'
