#!/bin/sh
# Update only installed distro packages, never replace third-party application binaries.
set -eu
suite="$1"; floors="$2"
case "$suite" in bookworm|trixie) ;; *) exit 1;; esac
. /etc/os-release
test "$ID" = debian
test "$VERSION_CODENAME" = "$suite"
test "$(id -u)" = 0
test -n "$floors"
test -r /usr/share/keyrings/debian-archive-keyring.gpg
export DEBIAN_FRONTEND=noninteractive
work="$(mktemp -d)"
trap 'rm -rf "$work"; rm -rf /var/lib/apt/lists/*' EXIT
# Restrict resolution to signed Debian repositories on the same release.
# A separate list directory and disabled package caches prevent stale vendor metadata.
printf '%s\n' \
 "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian $suite main" \
 "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian $suite-updates main" \
 "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian-security $suite-security main" > "$work/sources.list"
mkdir -p "$work/lists/partial"
chmod 755 "$work"
# POSIX sh has no slicing; use separate executable argument.
apt() {
    command="$1"; shift
    "$command" -o Dir::Etc::sourcelist="$work/sources.list" \
      -o Dir::Etc::sourceparts=- -o Dir::State::lists="$work/lists" \
      -o Dir::Cache::pkgcache= -o Dir::Cache::srcpkgcache= \
      -o Acquire::https::CaInfo=/tmp/jobbi-build-ca.pem -o Acquire::Retries=4 -o APT::Update::Error-Mode=any "$@"
}
apt apt-get update
set --
for spec in $floors; do
    pkg="${spec%%=*}"; minimum="${spec#*=}"
    test "$pkg" != "$minimum"
    case "$pkg" in ''|*[!a-z0-9+.-]*) exit 1;; esac
    test "$(dpkg-query -W -f='${Status}' "$pkg")" = 'install ok installed'
    installed="$(dpkg-query -W -f='${Version}' "$pkg")"
    if dpkg --compare-versions "$installed" ge "$minimum"; then continue; fi
    candidate="$(apt apt-cache policy "$pkg" | awk '$1=="Candidate:" {print $2; exit}')"
    test -n "$candidate" && test "$candidate" != '(none)'
    dpkg --compare-versions "$candidate" ge "$minimum"
    dpkg --compare-versions "$candidate" ge "$installed"
    set -- "$@" "$pkg=$candidate"
done
if [ "$#" -gt 0 ]; then
    apt apt-get install --yes --only-upgrade --no-remove --no-install-recommends "$@"
fi
for spec in $floors; do
    pkg="${spec%%=*}"; minimum="${spec#*=}"
    actual="$(dpkg-query -W -f='${Version}' "$pkg")"
    dpkg --compare-versions "$actual" ge "$minimum"
    printf 'Jobbi security package %s %s (minimum %s)\n' "$pkg" "$actual" "$minimum"
done
