# Physical appliance qualification

Use one spare x86-64 Linux machine or VM first; then qualify the exact physical SKU before sale. Do not run a full pilot on the personal production host without explicit authorization. No physical hardware has been ordered or tested by AIO CI.

Record exact model, CPU, RAM, PSU, bay count, SATA power and controller, storage filesystem, SSD and drives, SMART status, firmware, cooling, network, OS and Docker root. Verify new customer drives and lawful regional warranty. Check actual available capacity and tested independent backup. Do not format any disk containing existing data without owner approval.

Run preflight, fresh install and onboarding; test all selected apps with owned/generated sample media. Measure power at the wall for at least idle, one direct video stream, several concurrent streams/photo indexing, and recovery after reboot. Record average watts and temperatures. Measure installation hands-on time and total elapsed time separately. Test a network outage, power interruption using safe shutdown/reboot procedure, and backup restore onto a separate disk/instance. Verify customer tailnet ownership and HTTPS with another device. Test phones and TVs, including supported browsers and official client apps.

For NAS devices specifically, verify Docker Compose support, architecture, UID/GID mapping, Btrfs/volume permissions, local SSD database placement, storage expansion and image compatibility. Synology and ARM remain unqualified until demonstrated. Avoid selling transcoding capacity until measured on the exact server/software version.

Use business/ACCEPTANCE.md for each order; failing selected critical items block delivery. Record findings privately, not in this public repository. Never publish customer addresses, serials or private IP details.
