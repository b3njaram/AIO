# Storage manager (pilot)
 
The customer Storage page is read-only and displays measured filesystem capacity, detected direct Linux md RAID1 state and approved SMART results. Unknown is not healthy. RAID is not an independent backup. LVM, ZFS, Btrfs multi-device, hardware RAID and USB bridge health are not qualified by this manager.
 
On a dedicated appliance, install mdadm and inspect lsblk, /proc/mdstat, actual hardware IDs and backups. The technician tool never writes a disk:
 
    python3 scripts/storage-manager.py status --instance INSTANCE
    sudo python3 scripts/storage-manager.py create-mirror --disk /dev/disk/by-id/DRIVE_A --disk /dev/disk/by-id/DRIVE_B
    sudo python3 scripts/storage-manager.py replace-member --instance INSTANCE --backup COMPLETED_BACKUP --disk /dev/disk/by-id/NEW_DRIVE
    sudo python3 scripts/storage-manager.py expand-mirror --instance INSTANCE --backup COMPLETED_BACKUP
 
The creation plan requires two distinct empty whole disks with stable identities, no mounted filesystems, partitions, holders or signatures. No wipe, partition or format function is provided. Read-only signatures cannot prove the disk never held data: obtain approval before any write. After creation manually validate array name, mdadm persistent assembly, ext4 mount UUID and independent backup. Replacement is limited to a two-member RAID1 with exactly one healthy surviving member and one missing member, an independently verified archive of the same instance, and a sufficiently large blank disk. Failed-but-present member removal is deliberately manual. Expansion is limited to direct ext4 over an idle, synchronized RAID1 with both members larger than the current component size. Follow the printed plan under a maintenance window, verify actual restore and monitor synchronization. Do not automatically run the printed commands. Record UUIDs, disk IDs and acceptance evidence privately.
 
Unit tests cover topology and refusal rules. Real mdadm assembly, replacement, synchronization and filesystem growth remain qualification requirements; never perform a live fault drill on a customer's only data copy.

Replacement and expansion reject overlapping OS/Docker/backup block-device ancestry. The current planner is intentionally limited to an array dedicated to application data, not Docker's own root filesystem. Verify hardware RAID or unusual controller configurations separately.
