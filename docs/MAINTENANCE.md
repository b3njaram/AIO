# Customer maintenance and safe updates

Run diagnostics locally on the customer server, not on your personal server for a remote customer. No SSH credentials are saved by AIO.

    python3 scripts/diagnostics.py /path/to/customer-instance

Reports data and Docker free space, RAM, load, available thermal sensors, block devices and service state. SMART is opt-in: add --smart-device /dev/sda (repeat for each exact authorized disk) to diagnostics.py or maintenance.py. It reads smartctl JSON health and relevant attributes, never runs a self-test or writes to drives. Install smartmontools separately, and use appropriate local permissions; missing/unsupported SMART reports unknown, not healthy. On the customer machine, identify each exact disk with lsblk, then use authorized read-only smartctl -H -A /dev/DEVICE (smartmontools may need installation and sudo). Never assume a USB bridge reports SMART. Check manufacturer thresholds and replace failing storage only with approval. No automatic disk writes, tests, reformatting or repairs.

Create a dedicated independent backup filesystem, preferably encrypted, mounted persistently with restricted permissions. Confirm actual mount and available capacity, including the entire media library. The maintenance runner refuses the same filesystem as the instance, but that alone does not prove independent physical disks. Do not use a directory on the OS disk as an independent backup.

    python3 scripts/maintenance.py /path/to/customer-instance /path/to/mounted-backups
    python3 scripts/maintenance.py /path/to/customer-instance /path/to/mounted-backups --run-backup

Second command explicitly permits cold backup downtime. Verify output and restart state. The script saves a private maintenance.json status and returns nonzero on warnings, including stale/missing backups and service failures. Hashes verify integrity, not recoverability; practice actual isolated restoration. No automatic deletion, pruning or upgrade. Set --minimum-free-gib based on full backup size; the default is only a minimum. Keep multiple backup generations and an offsite copy. Manual retention after successful recovery drill.

## Schedule only after customer approval
On the customer host, use its systemd user timer or equivalent. Example user unit with actual absolute paths (not placeholders), ExecStart=/usr/bin/python3 /path/to/AIO/scripts/maintenance.py /path/to/customer-instance /path/to/mounted-backups --run-backup . Use Type=oneshot. Timer OnCalendar=Sun *-*-* 03:00:00, Persistent=false; enable only after confirming expected downtime, backup mount and service permissions. A user timer runs only while its user manager is active; confirm policy for reboot/lingering. Use journalctl --user -u YOUR_UNIT for local alerts. No email/SMS notifications are sent automatically; configure customer-owned Uptime Kuma notifications only with their consent. Test a failed backup and a reboot before relying on scheduling.

## Updates and rollback
1. Read release notes, security issues and upstream compatibility. Check proposed exact image tags/digests and AIO commit, no blind docker compose pull.
2. Confirm independent full backup and restoration on a separate project. Record release.json and current image IDs; retain compatible images and old deployment snapshot. Schedule outage with customer.
3. Validate new version on a disposable test installation first. Do not mutate existing deployment files or run automatic update agents.
4. Only after passing app-specific acceptance and customer approval, apply a documented upgrade for that version. For failed or incompatible migration, stop the new project and recover the pre-upgrade data and compatible images in a separate project. Do not downgrade migrated databases in place. Confirm private HTTPS origin and handoff.
5. Record the change in the private service record. AIO does not yet automate an in-place upgrade or automatic rollback; no unattended updates.

## Physical pilot
Follow HARDWARE-QUALIFICATION.md and business/ACCEPTANCE.md. Record actual wall power, thermals, simultaneous workloads, installation time and recovery. No CI run certifies physical hardware.

## Optional schedule generator

On the actual customer host, preview first:

    python3 scripts/schedule-backups.py /path/to/customer-instance /path/to/mounted-backups

After explicit approval of weekly downtime, actual mount independence and sufficient free space:

    python3 scripts/schedule-backups.py /path/to/customer-instance /path/to/mounted-backups --hour 3 --enable

It refuses existing conflicting units and same-filesystem backups. It only creates a user timer for the specified validated instance. No system-wide changes or automatic retention. Check user manager startup and backup log after the first scheduled run. A backup or restart failure returns nonzero; examine maintenance.json and journal. Never run this against the owner production server merely to test.
