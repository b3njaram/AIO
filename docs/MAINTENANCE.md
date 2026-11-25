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

## Actual image inventory

    python3 scripts/release-inventory.py INSTANCE --record

New cold backups include the image inventory and a compressed archive of locally built images. Recovery loads these by image ID and pins pulled services to a recorded registry digest. Keep registry access available on a replacement machine. The integrity manifest covers both image and data archives. Restore with `--require-exact-images`. Compose creates stopped containers without rebuilding and compares every image ID before copying named volume data. Older backups can require the original engine cache or a manual migration. A digest identifies image contents and does not establish vulnerability status.

If backup power or execution was interrupted, inspect the project and run `bash scripts/backup.sh INSTANCE --resume` to start exactly the services that were running before the cold backup. A subsequent backup refuses to start while that journal exists. Only a directory with a completed and verified SHA256SUMS is eligible for recovery. After a crash, verify recovered application health. Checksums detect corruption. Maintain custody of backups containing secrets.

For optional failure notification, add `--failure-unit your-notifier.service` to the schedule preview and enable commands. Supply a customer-owned systemd user service that delivers the notification. Inspect its own journal to confirm receipt. No third-party account is required.

## Storage Manager
See [STORAGE.md](STORAGE.md) for read-only RAID1 status and technician disk preparation, replacement and expansion plans. No web endpoint executes disk operations.

## Recovery Center: supervised offline trial

The new recovery-center.py provides a technician catalog of completed manifests, explicit checksum and identity verification, strict stopped restore, staged update and rollback. Capture the approved backup filesystem fingerprint from backup_mount.mount_identity; the tool refuses mount substitution and a backup sharing the Docker filesystem. Use a dedicated customer host only.

    python3 -c 'import sys;sys.path.insert(0,"scripts");from backup_mount import mount_identity;print(mount_identity(sys.argv[1]))' BACKUP_ROOT

    python3 scripts/recovery-center.py catalog INSTANCE BACKUP_ROOT --mount-id FINGERPRINT
    python3 scripts/recovery-center.py verify INSTANCE BACKUP_ROOT --mount-id FINGERPRINT --backup EXACT_DIRECTORY_NAME
    python3 scripts/recovery-center.py restore INSTANCE BACKUP_ROOT --mount-id FINGERPRINT --backup EXACT_DIRECTORY_NAME --candidate restored --base-port 19080

Add --apply to restore only after verifying capacity and intended target. It creates a stopped copy. A manifest alone is not verified integrity.

For a final update trial, check out the exact reviewed target revision with full Git history. Disable private routes, restore local origins, coordinate a customer maintenance window and prevent external writes. Confirm a separate physical backup, enough space for full image/data archives and a parallel copy.

    python3 scripts/recovery-center.py stage INSTANCE BACKUP_ROOT --mount-id FINGERPRINT --candidate trial --base-port 19080 --to-commit FULL_REVIEWED_SHA

Add --apply to perform a final cold backup with all images, hold the original offline and stage a separate stopped candidate. If staging fails, inspect the exact hold and any partial candidate; do not delete or overwrite it. An interruption before the hold is fully committed can resume the source through the normal backup journal; the trial refuses to start if the source is running.

    python3 scripts/recovery-center.py start-trial INSTANCE BACKUP_ROOT --mount-id FINGERPRINT --candidate trial --apply

This checks reachability, not functional acceptance. Keep the trial loopback-only with no public or private customer routes until a technician completes every selected application's acceptance. Do not allow real customer writes during testing. On rollback:

    python3 scripts/recovery-center.py rollback INSTANCE BACKUP_ROOT --mount-id FINGERPRINT --candidate trial --confirm-no-candidate-writes --apply

The tool stops the linked candidate and restarts the original exact service set; it retains both datasets and the backup. If a partial candidate has no valid link journal, inspect it manually before recovery. Never start both with real users. Production cutover, transferring systemd timers, private HTTPS, customer data reconciliation after real writes and retiring the original remain supervised tasks; this is not an unattended migration. No automatic deletion or rollback of migrated databases.
