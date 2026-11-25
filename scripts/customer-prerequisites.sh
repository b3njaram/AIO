#!/usr/bin/env bash
# Run as the customer operator on a fresh Ubuntu 24.04 x86-64 appliance.
set -euo pipefail
case "${1:---preview}" in
  --preview|--install) mode="${1:---preview}" ;;
  *) echo 'Usage: customer-prerequisites.sh [--preview|--install]' >&2; exit 2 ;;
esac
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && "$(uname -m)" == x86_64 ]] || {
  echo 'Automatic package setup supports Ubuntu 24.04 x86-64. Use preflight.py to inspect another host.' >&2; exit 1;
}
if command -v docker >/dev/null; then
  docker compose version
  docker info --format '{{.ServerVersion}}'
  echo 'Existing Docker installation detected. Existing package configuration retained.'
  exit 0
fi
packages=(docker.io docker-compose-v2 python3 git curl util-linux smartmontools)
printf 'Customer host packages: %s\n' "${packages[*]}"
[[ "$mode" == --install ]] || exit 0
[[ $EUID -eq 0 ]] || { echo 'Run --install with sudo on the dedicated customer host.' >&2; exit 1; }
for path in /var/lib/docker /var/lib/containerd /etc/docker; do
  if [[ -e "$path" ]]; then echo "Existing runtime state at $path. Review manually." >&2; exit 1; fi
done
apt-get update
apt-get --simulate --no-remove install "${packages[@]}" >/dev/null
apt-get --yes --no-remove install "${packages[@]}"
systemctl enable --now docker
docker compose version
docker info --format '{{.ServerVersion}}'
echo 'Confirm the customer installation account has intentional Docker access, then run preflight.py as that account.'
