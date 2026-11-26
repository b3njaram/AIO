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
# APK 2 and 3 both store installed package records as P:/V: fields.
# Human-readable "apk info" output changes by apk version and verbosity.
db=/lib/apk/db/installed
test -s "$db"
names() { awk '/^P:/ {print substr($0,3)}' "$db" | sort -u; }
names > "$work/before"
set --
for spec in $floors; do
    pkg="${spec%%=*}"; minimum="${spec#*=}"
    test "$pkg" != "$minimum"
    case "$pkg" in ''|*[!a-z0-9+._-]*) exit 1;; esac
    apk info -e "$pkg" >/dev/null
    set -- "$@" "$pkg>=$minimum"
done
apk add --no-cache --upgrade "$@"
names > "$work/after"
test -z "$(comm -23 "$work/before" "$work/after")"
for spec in $floors; do
    pkg="${spec%%=*}"; minimum="${spec#*=}"
    actual="$(awk -v pkg="$pkg" '/^P:/ {name=substr($0,3)} /^V:/ && name==pkg {print substr($0,3); exit}' "$db")"
    test -n "$actual" || { echo "Missing installed version for $pkg" >&2; exit 1; }
    case "$(apk version -t "$actual" "$minimum")" in "="|">") ;; *) exit 1;; esac
    printf 'Jobbi security package %s %s (minimum %s)\n' "$pkg" "$actual" "$minimum"
done
