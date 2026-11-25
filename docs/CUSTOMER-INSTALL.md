# Guided JobbiSoft Home installation (pilot)
 
## Standard host
 
Ubuntu Server 24.04 LTS x86-64, no desktop, one dedicated customer-owned machine or VM. Use a local SSD for Linux/Docker databases; size RAM and media storage to workload. Start with 16 GB RAM (32 GB for larger workloads); test actual capacity, thermals and transcoding. No unattended OS disk formatting is supported. Use the official Ubuntu installer, explicit approved disk selection, customer-local operator account and optional OpenSSH.
 
## One command after OS setup
 
Mount the reviewed data and independent backup filesystems first. Verify persistence in /etc/fstab, physical disk identities, ownership and capacity; do not reuse a personal server's data directory. On the dedicated host, install Git if necessary:
 
    sudo apt update
    sudo apt install git python3
    git clone https://github.com/b3njaram/AIO.git ~/jobbi-aio
    cd ~/jobbi-aio
 
Check out a reviewed release commit rather than arbitrary main or an unvalidated branch. For pilot testing only use the reviewed candidate SHA.
 
    python3 scripts/setup-customer.py --name home --data-root /srv/jobbi-data --backup-root /mnt/jobbi-backup
 
Review the command plan, then repeat with --apply. The setup installs Docker packages if absent, checks capacity and Docker access, creates the instance, starts selected apps, waits for HTTP reachability and prints onboarding instructions. If Docker access is missing, grant it intentionally only to the trusted local operator (Docker group is root-equivalent), log out/in and rerun before any instance was created. Existing Docker configuration is retained. Core apps default to all except Pi-hole. Optional --quote /path/to/jobbi-home-config.json selects the customer apps; --apps explicitly overrides it. Prices, mirroring and disk capacity are never treated as hardware validation. The script refuses existing instances and does not erase data. If stopped after instance preparation, inspect the progress and frozen deployment rather than deleting or rerunning blindly.
 
Docker restart policies bring services back when the enabled daemon starts. Test a real reboot and mount availability. There is no desktop login requirement. Separate OS/volume failure and backup recovery are still physical acceptance tests.
 
## Customer participation
 
Complete docs/HANDOFF.md for application accounts and sample-data tests. Use trusted SSH forwarding for initial setup, then a customer-owned Tailscale account and private HTTPS per docs/PRIVATE-ACCESS.md. No personal tailnet credentials, public Funnel, public router ports or automatic DNS changes. Use the maintenance guide for independent encrypted backup, restore and supervised upgrades. Never mark a service accepted solely because HTTP responds.
 
## Future installer
 
A USB-based Ubuntu autoinstall workflow can automate packages, the operator setup and first-boot provisioning, but must identify and explicitly confirm the intended OS disk before erasing it. Keep account enrollment and recovery secrets customer-controlled. An unattended ISO and real-machine first-boot/reboot verification are not implemented or certified yet.

## USB seed generator (pilot)

On a trusted Linux workstation, install openssl, cloud-image-utils and optionally xorriso. Obtain the official Ubuntu Server 24.04 ISO and verify its signed checksum separately. Prepare and identify existing formatted data and backup filesystems by UUID. Use the seed builder, which prompts for the customer's local operator password and accepts a public SSH key:

    python3 scripts/make-install-usb.py --name home --commit FULL_REVIEWED_COMMIT --data-uuid DATA_UUID --backup-uuid BACKUP_UUID --ssh-key-file ~/.ssh/id_ed25519.pub --out ~/private-home-seed

Use cloud-localds to create a separate NoCloud seed ISO from user-data and meta-data, or add --ubuntu-iso PATH --iso-sha256 VERIFIED_SHA256 to generate a customized installation ISO. No command flashes a drive. Boot the official installer/seed or customized ISO and review interactive storage selection; disconnect unrelated drives if possible. Never select the preformatted data/backup devices for erasure. Keep the seed private. First boot mounts the exact approved UUIDs, fetches the pinned AIO revision, installs a Docker storage guard before provisioning and starts the stack. If a required disk is absent the service fails without installing; inspect journalctl -u jobbi-first-boot and restart only after verifying mounts. An incomplete existing installation is never automatically overwritten. Physical boot/UEFI and autoinstall schema validation still require a disposable VM and actual appliance.

## Guided owner setup and maintenance

Run locally on the appliance before private HTTPS: `python3 scripts/setup-accounts.py INSTANCE --email owner@example.com` (preview), then add --apply. The wizard prompts separate passwords for supported selected apps and verifies login; no passwords are persisted. Existing credentials are not reset by default. Finish Vaultwarden and Uptime Kuma in native UI and enroll the customer's own Tailscale account. Use onboard.py to mark each app only after actual functional verification. The customer launcher now contains Setup and Maintenance pages; no Docker socket or write endpoints are added.

First boot enables a systemd health timer and a backup-journal resume service. Manual installs can preview `python3 scripts/install-health-service.py INSTANCE BACKUP --operator OWNER --check-updates`, then use sudo with --apply on the dedicated appliance. Explicit --smart-device /dev/sda flags permit read-only SMART queries from a reviewed root-owned checkout; no drive is auto-selected. Health data is stale after 45 minutes and missing values remain unknown. Only approved Jobbi release tags are checked; no automatic upgrades. Configure separate encrypted backups and approve weekly backup downtime using schedule-backups.py. Test missing disks and reboot, actual SMART access and actual restore before delivery.

The USB generator accepts --weekly-backup only after the customer explicitly approves the weekly Sunday 03:00 cold-backup interruption. System-level timers run without an interactive login. First boot attempts SMART only on stable whole-drive aliases associated with the explicitly approved data and backup filesystem UUIDs; unsupported devices are reported unknown, not healthy. On manual guided installation the dedicated-host Docker storage guard is installed before creating containers. Verify actual disk layout, boot guard, SMART and backup independence in person.

## Validate before distribution

The `Headless Ubuntu first-boot VM` GitHub workflow tests the exact generated installed-system payload using a disposable cloud-image VM and sparse file-backed drives. Its tests do not replace physical USB/UEFI verification. Run the actual custom ISO through Subiquity and the physical hardware acceptance process separately. See HARDWARE-QUALIFICATION.md.

The local account wizard also supports Uptime Kuma using the Ubuntu python3-socketio package, and --invite-vault sends an explicit invitation to the intended customer address; the native client must create its own master password and encryption keys. For remote installs, the signed Tailscale package is installed without enrollment. Once the owner enrolls their own tailnet and approves ACLs, finish-private-access.py previews or applies the journaled private HTTPS setup. Manual guided installs also enable a health timer and interrupted-backup resume service without an interactive login; add --weekly-backup only with customer approval.
