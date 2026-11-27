#!/usr/bin/env bash
# Use the runner's Ubuntu archive without consulting third-party source files.
set -euo pipefail
(( $# > 0 ))
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_CODENAME" == noble ]]
sources=/etc/apt/sources.list.d/ubuntu.sources
test -r "$sources"
grep -Fxq 'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg' "$sources"
options=(
  -o "Dir::Etc::sourcelist=$sources"
  -o Dir::Etc::sourceparts=-
  -o Acquire::Retries=4
  -o APT::Update::Error-Mode=any
)
sudo apt-get "${options[@]}" update
sudo DEBIAN_FRONTEND=noninteractive apt-get "${options[@]}" install -y --no-install-recommends "$@"
