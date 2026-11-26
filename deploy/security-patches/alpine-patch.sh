#!/bin/sh
# Keep upstream signed stable repositories and all existing runtime packages.
set -eu
test "$(id -u)" = 0
. /etc/os-release
test "$ID" = alpine
test -n "$1"
floors="$1"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
# Refuse rolling edge repositories rather than mixing incompatible branches.
if grep -Eq '(^|/)edge(/|$)' /etc/apk/repositories; then exit 1; fi
apk info | sort -u > "$work/before"
set --
for spec in $floors; do
    pkg="${spec%%=*}"; minimum="${spec#*=}"
    test "$pkg" != "$minimum"
    case "$pkg" in ''|*[!a-z0-9+._-]*) exit 1;; esac
    apk info -e "$pkg" >/dev/null
    set -- "$@" "$pkg>=$minimum"
done
apk add --no-cache --upgrade "$@"
apk info | sort -u > "$work/after"
test -z "$(comm -23 "$work/before" "$work/after")"
for spec in $floors; do
    pkg="${spec%%=*}"; minimum="${spec#*=}"
    actual="$(apk info -v "$pkg" | head -n 1)"
    case "$actual" in "$pkg"-*) actual="${actual#"$pkg"-}";; *) exit 1;; esac
    case "$(apk version -t "$actual" "$minimum")" in "="|">") ;; *) exit 1;; esac
    printf 'Jobbi security package %s %s (minimum %s)\n' "$pkg" "$actual" "$minimum"
done
