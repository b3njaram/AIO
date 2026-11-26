# JobbiSoft Home development tracker

The integration branch is `release/exact-recovery`, [PR 2](https://github.com/b3njaram/AIO/pull/2). PR 1 was merged. Keep this branch in pilot status. The authoritative acceptance rules are in [the release gate](RELEASE-GATE.md).

## Recent implementation and evidence

| Change | Verified evidence | Remaining gate |
| --- | --- | --- |
| 31960b22 switched Vaultwarden to the pinned Alpine variant of the same application version and added per-image CycloneDX inventories | [Scan and SBOMs](https://github.com/b3njaram/AIO/actions/runs/45758014938) recorded zero gated findings for Vaultwarden and 2,107 summed findings across the stack, down from 2,313 | Triage affected packages, upstream fixes, runtime compatibility and licenses before distribution |
| c78e29e1 added a disconnected Ubuntu 24.04 amd64 package payload, standalone Git revision, exact application bundle, media checksums and private ISO generation | [First disconnected drill](https://github.com/b3njaram/AIO/actions/runs/45758262623) found an APT file-permission failure | Rerun after package permissions fix, then boot actual installer with external networking disabled |
| 4d4457e8 added isolated application container removal and recreation with exact mount and image checks, pinned Alpine Valkey, named the photo queue and blocked upgrades from unmanaged photo queues | [Lifecycle pilot](https://github.com/b3njaram/AIO/actions/runs/45758577689) exposed a Kuma owner-session timeout | Repeat lifecycle and application data checks on the exact proposed release |
| Pilot source packaging | ISO workflow emits a source archive, manifest and SHA256SUMS after comparing two builds | Source artifact is for inspection. Build personalized media privately from the reviewed checkout |

## Continuation by product area

Use the repository phase grouping in the linked guides. Keep customer-specific evidence off Git.

| Repository workstream | Implemented | Acceptance still required |
| --- | --- | --- |
| 1–2 Installation and onboarding | USB remaster, explicit OS disk selection, mounted data/backup UUIDs, first boot and temporary browser setup | Full disconnected Subiquity install, account setup, private second-device access, beginner walkthrough |
| 3–5 Startup, maintenance and qualification | Storage guard, reboot and missing-disk VM, health and SMART reporting, hardware checklist | Exact hardware power cut, reattachment, RAID resync, thermal, power and storage measurements |
| 6 Maintenance and security | Private HTTPS configuration, rollback, loopback isolation checks, optional alerts, image scanning | Tailnet ACL allow/deny, TLS and cookies on customer devices, security remediation, notification delivery |
| 7–10 Performance, UPS, delivery and commercial readiness | Capacity probe, UPS tooling, bilingual handoff, private cash records and launch review | Physical measurements, actual UPS shutdown, customer handoff, license and warranty review |
| 11 Offline installation and recovery | Exact-image and source bundles, independent storage checks, local package repository, staged upgrades | Disconnected boot including repeat backup on replacement hardware, interrupted update and recovery with real disks |
| 12–15 Fleet, private maintenance and mobile | Owner records, temporary private management, monitor configuration, branded browser launcher | Native iOS/Android acceptance, broader customer UI app installation/removal, end-to-end language and accessibility review |
| 16 Migration | Verified file staging and native application import procedures | Actual source-specific imports and independent restore with representative customer-owned data |
| 17–20 Backup catalog, mobile, handoff and qualification | Detailed catalog, mobile favorites, bilingual checksummed delivery pack and exact-revision readiness report | Independent restore, full regression on a single revision, licenses and final customer acceptance |

## Reproducing the release decision

Run `python3 scripts/release-readiness.py FULL_COMMIT` against a completed release-gate push. Inspect failures in Actions, including the per-image report. Open the ISO workflow artifact for reproducible pilot source. Follow [customer installation](CUSTOMER-INSTALL.md), [offline media](OFFLINE-INSTALL.md), [private access](PRIVATE-ACCESS.md), and [physical qualification](HARDWARE-QUALIFICATION.md). Work on isolated new instances. Record software passes with a revision and run URL, and physical passes only with actual device evidence. No commercial candidate has been approved.
