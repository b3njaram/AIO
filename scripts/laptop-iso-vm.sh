#!/usr/bin/env bash
set -euo pipefail
iso=$(realpath "$1")
mkdir "$2"
cd "$2"
for firmware in BIOS UEFI; do
    args=()
    if [[ "$firmware" == UEFI ]]; then
        # Split OVMF builds require matching code and variable pflash devices.
        code=$(dpkg -L ovmf | awk '/\/OVMF_CODE_4M[.]fd$/ {print; exit}')
        vars=$(dpkg -L ovmf | awk '/\/OVMF_VARS_4M[.]fd$/ {print; exit}')
        if [[ ! -r "$code" || ! -r "$vars" ]]; then
            code=$(dpkg -L ovmf | awk '/\/OVMF_CODE[.]fd$/ {print; exit}')
            vars=$(dpkg -L ovmf | awk '/\/OVMF_VARS[.]fd$/ {print; exit}')
        fi
        test -r "$code" && test -r "$vars"
        cp "$vars" UEFI-vars.fd
        args=(-drive "if=pflash,format=raw,readonly=on,file=$code"
              -drive "if=pflash,format=raw,file=UEFI-vars.fd")
    fi
    truncate -s 96G "$firmware.img"
    qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 2 -m 3072 \
        -display none -monitor "unix:$firmware.sock,server=on,wait=off" -serial "file:$firmware.log" -no-reboot \
        -drive "file=$firmware.img,format=raw,if=virtio" -nic none -cdrom "$iso" -boot order=d "${args[@]}" &
    vm=$!
    trap 'kill "$vm" 2>/dev/null || true' EXIT
    passed=false
    for attempt in {1..120}; do
        if grep -q JOBBI_RC_INSTALLER_READY "$firmware.log"; then passed=true; break; fi
        kill -0 "$vm" || break
        if [[ "$attempt" == 3 || "$attempt" == 6 ]]; then
            python3 - "$firmware.sock" <<'PYCODE'
import socket
import sys

with socket.socket(socket.AF_UNIX) as client:
    client.settimeout(3)
    client.connect(sys.argv[1])
    client.recv(4096)
    client.sendall(b"sendkey ret\n")
    client.recv(4096)
PYCODE
        fi
        sleep 5
    done
    kill "$vm" 2>/dev/null || true
    wait "$vm" 2>/dev/null || true
    trap - EXIT
    rm -f "$firmware.img" "$firmware.sock" UEFI-vars.fd
    if [[ "$passed" != true ]]; then echo "$firmware did not reach Subiquity early commands"; exit 1; fi
    echo "$firmware reached Subiquity using embedded seed from the downloadable media"
done
