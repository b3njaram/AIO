#!/usr/bin/env bash
set -euo pipefail
iso=$(realpath "$1")
mkdir "$2"
cd "$2"
for firmware in BIOS UEFI; do
    args=()
    if [[ "$firmware" == UEFI ]]; then
        args=(-bios /usr/share/OVMF/OVMF_CODE_4M.fd)
    fi
    qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 2 -m 3072 \
        -display none -monitor none -serial "file:$firmware.log" -no-reboot \
        -nic none -cdrom "$iso" -boot order=d "${args[@]}" &
    vm=$!
    trap 'kill "$vm" 2>/dev/null || true' EXIT
    passed=false
    for _ in {1..120}; do
        if grep -q JOBBI_RC_INSTALLER_READY "$firmware.log"; then passed=true; break; fi
        kill -0 "$vm" || break
        sleep 5
    done
    kill "$vm" 2>/dev/null || true
    wait "$vm" 2>/dev/null || true
    trap - EXIT
    if [[ "$passed" != true ]]; then echo "$firmware did not reach Subiquity early commands"; exit 1; fi
    echo "$firmware reached Subiquity using embedded seed from the downloadable media"
done
