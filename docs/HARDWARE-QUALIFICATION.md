# Physical appliance qualification

Use one spare x86-64 Linux machine or VM first; then qualify the exact physical SKU before sale. Do not run a full pilot on the personal production host without explicit authorization. No physical hardware has been ordered or tested by AIO CI.

Record exact model, CPU, RAM, PSU, bay count, SATA power and controller, storage filesystem, SSD and drives, SMART status, firmware, cooling, network, OS and Docker root. Verify new customer drives and lawful regional warranty. Check actual available capacity and tested independent backup. Do not format any disk containing existing data without owner approval.

Run preflight, fresh install and onboarding; test all selected apps with owned/generated sample media. Measure power at the wall for at least idle, one direct video stream, several concurrent streams/photo indexing, and recovery after reboot. Record average watts and temperatures. Measure installation hands-on time and total elapsed time separately. Test a network outage, power interruption using safe shutdown/reboot procedure, and backup restore onto a separate disk/instance. Verify customer tailnet ownership and HTTPS with another device. Test phones and TVs, including supported browsers and official client apps.

For NAS devices specifically, verify Docker Compose support, architecture, UID/GID mapping, Btrfs/volume permissions, local SSD database placement, storage expansion and image compatibility. Synology and ARM remain unqualified until demonstrated. Avoid selling transcoding capacity until measured on the exact server/software version.

Use business/ACCEPTANCE.md for each order; failing selected critical items block delivery. Record findings privately, not in this public repository. Never publish customer addresses, serials or private IP details.

## Evidence collector and reboot drill

On the dedicated candidate, run `python3 scripts/qualify-appliance.py INSTANCE BACKUP --output ~/private-before-reboot.json` (add explicit --smart-device for authorized checks). After a controlled reboot, run the same command with `--before ~/private-before-reboot.json --output ~/private-after-reboot.json`. It validates the newest completed archive checksum, records the software release, mount fingerprints, observed service states and available RAID status, and compares boot IDs. The report is not a hardware certification. Record exact physical measurements and complete each manual check above; do not claim hardware qualification based on the VM.

The dedicated Headless Ubuntu first-boot VM CI workflow exercises the same generated installed-system cloud-init payload on sparse file-backed disks, using an official checksum-pinned Ubuntu cloud image. It checks automatic first boot, simulated power loss with a backup journal, data persistence, missing-disk fail-closed Docker startup and reattachment. It does not exercise the Subiquity installer UI, actual USB boot, firmware, real RAID, wall power, real SMART or physical power loss. The exact release and CI job conclusion must be recorded separately.

The hosted VM test uses QEMU software emulation because nested KVM is not reliable on the CI runner. The cloud image SHA256 is pinned; upstream changes require review rather than silently booting a different image.

Configure BIOS/UEFI restore-on-AC-power-loss to power on (with customer approval) and test it using safe, disposable test data. An optional UPS and monitored shutdown should be qualified; software cannot turn on hardware whose firmware remains powered off. Record the installed ISO checksum, firmware boot mode, OS disk selection and actual reboot/restore findings privately.
