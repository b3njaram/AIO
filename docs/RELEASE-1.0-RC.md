# JobbiSoft Home 1.0 release candidate

This connected lab installer consolidates the physical one-boot pilot, customer service changes and exact-image recovery branch. See REVISION for the exact source. The image contains no appliance account passwords, pairing tokens or keys. Ubuntu verifies and installs host packages and the first-boot service retrieves the pinned Git commit. Independent recovery media and optional app integrations have separate qualification requirements.

## Install on a spare SSD

1. Extract the workflow artifact. Run `sha256sum -c SHA256SUMS` next to the ISO.
2. On Fedora, open Fedora Media Writer, choose Custom Image and select the verified ISO. Confirm the spare USB by name and capacity. Writing replaces that USB's contents.
3. Disconnect unrelated disks, boot the USB and inspect the storage summary. Select the intended spare OS disk with guided LVM, leaving at least 68 GiB free in the volume group. Approve erasure only for the selected disk.
4. Choose an operator and unique local password. Connect Ethernet to an isolated private network and allow Internet access for first boot. Remove the USB at reboot.
5. Read tty3 on the appliance for the temporary browser setup address, fingerprint and pairing code. Verify the TLS fingerprint before entering credentials. Finish the Vaultwarden master password in its native client.
6. Confirm login and real sample data operations. The legacy paired client gateway is a lab feature. Its address and certificate are tied to the LAN IP. The optional customer-owned private tailnet path still requires manual qualification.

## Existing laptop

Keep the working SSD and its data in place. Use a separate verified backup and spare disk for an RC trial. The dashboard-only update script and staged recovery tools are separate paths. A full in-place migration of the working laptop to this exact image is pending. Review MAINTENANCE.md and test an isolated restore before moving data.

## Qualification and distribution

The connected image targets x86-64 systems with Ethernet, guided Ubuntu LVM and enough free space for a separate data LV. The proven test machine used an Intel Core i7-3537U, 16 GB RAM and a Kingston 480 GB SSD. The operator reported about 3 GB idle memory during the earlier full-stack trial. Prior physical results apply to the prior pilot only. Test firmware boot, reboot, load, independent encrypted backup and recovery, and second-device allow/deny on this revision.

Kuma remains accessible from Monitoring with its own complete UI. The optional Soulseek, Invidious and Pi-hole paths are pilots. Verify provider authentication, authorized search/import and playback, DNS behavior and independent recovery before enabling them. The tagged commercial release depends on exact-revision workflow results, image security remediation, customer networking acceptance, and review of upstream redistribution notices, licenses and service terms. See SECURITY-REMEDIATION.md and the Actions SBOM artifact. Preserve upstream notices on any approved redistribution.

For optional Invidious, upstream documents its companion and database deployment and capacity requirements. Tailscale Personal is offered for non-commercial use. Evaluate each customer's use before making remote access part of an offering. Review the Ubuntu intellectual property policy before any commercial redistribution of a remastered image.

- [Canonical intellectual property policy](https://canonical.com/legal/intellectual-property-policy)
- [Tailscale pricing and plan terms](https://tailscale.com/pricing)
- [Invidious installation requirements](https://docs.invidious.io/installation/)
