# JobbiSoft Home development tracker

The integration branch is `release/exact-recovery`, [PR 2](https://github.com/b3njaram/AIO/pull/2). PR 1 was merged. Keep this branch in pilot status. The authoritative acceptance rules are in [the release gate](RELEASE-GATE.md).

## Recent implementation and evidence

| Change | Verified evidence | Remaining gate |
| --- | --- | --- |
| 31960b22 switched Vaultwarden to the pinned Alpine variant of the same application version and added per-image CycloneDX inventories | [Scan and SBOMs](https://github.com/b3njaram/AIO/actions/runs/45758014938) recorded zero gated findings for Vaultwarden and 2,107 summed findings across the stack, down from 2,313 | Triage affected packages, upstream fixes, runtime compatibility and licenses before distribution |
| c78e29e1 added a disconnected Ubuntu 24.04 amd64 package payload, standalone Git revision, exact application bundle, media checksums and private ISO generation | [First disconnected drill](https://github.com/b3njaram/AIO/actions/runs/45758262623) found an APT file-permission failure | Rerun after package permissions fix, then boot actual installer with external networking disabled |
| 4d4457e8 added isolated application container removal and recreation with exact mount and image checks, pinned Alpine Valkey, named the photo queue and blocked upgrades from unmanaged photo queues | [Lifecycle pilot](https://github.com/b3njaram/AIO/actions/runs/45758577689) exposed a Kuma owner-session timeout | Repeat lifecycle and application data checks on the exact proposed release |
| Pilot source packaging | ISO workflow emits a source archive, manifest and SHA256SUMS after comparing two builds | Source artifact is for inspection. Build personalized media privately from the reviewed checkout |

The complete [4d4457e8 scan](https://github.com/b3njaram/AIO/actions/runs/45758577676) recorded 2,036 findings at gated severities. The media, library, office, isolation, full-stack and staged-upgrade jobs passed on that revision. Infrastructure recovery failed during Kuma monitor configuration. New offline installations and recoveries now preserve original upstream archives and the local helper ID so they can generate the next independent recovery kit. Verify the chained recovery in the media pilot and the fresh disconnected installation in its own workflow.

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

## Recovery and security remediation follow-up

At fc8f2016 the VM passed initial boot, interrupted backup resume, abrupt reboot and missing-data-disk protection, but the reattached dashboard was exited (137) even with the correct mounts and active Docker. The new boot unit runs as the original operator, after backup recovery, verifies the recorded data filesystem identity, honors update holds and backup journals, and starts only the existing mandatory launcher. No application is recreated or pulled. The infrastructure pilot reached restored Kuma owner login but a later polling login timed out; monitor configuration now uses local WebSocket transport and bounded retries of connection/login timeouts only, not rejected credentials or mutations. Both require fresh real CI evidence.

The latest image scan failed before scanning due to registry throttling. Candidate pulls/builds now have bounded retries, lower parallelism and optional Docker Hub credentials; the scanner emits a package remediation queue while retaining all gated findings. This does not resolve third-party CVEs or waive commercial security review. Keep the full Kuma feature set (no unapproved slim-image replacement). Review package fixes using the new exact-revision report before changing any upstream digest.

The follow-up candidate retains Kuma 2.5.12 full, with Debian's exact signed Chromium and chromium-common 156.0.8078.108-1~deb12u1 security update ([DLA-4932-1](https://lists.debian.org/debian-lts-announce/2026/11/msg00057.html)). Its prior scan reported 206 fixable findings per package (412 summed); the actual post-update count must come from the new exact-image scan. Installed optional matching Chromium packages are also updated without removing unrelated packages. The full-image build is now local, so exact-image backup includes it; a pinned package disappearing from the signed repository stops builds rather than silently substituting versions. The infrastructure pilot validates package versions and embedded browser rendering before and after recovery. No upstream feature was removed; no remaining security findings are waived. Do not distribute the candidate until the full release gates pass.

The 43a838b release-gate runs completed: all eight non-security workflows passed, including the full application pilot and VM recovery. The [completed scan](https://github.com/b3njaram/AIO/actions/runs/45763697446) found 1,624 gated findings (412 fewer than the previous completed scan). See [SECURITY-REMEDIATION.md](SECURITY-REMEDIATION.md) for the next targeted OS package candidate. The new revision requires fresh validation and is not approved for release.

Follow-up on fa9d3109: APK post-upgrade verification was repaired at f378f7cc. Subsequent work addresses Debian HTTPS trust during image builds and Kuma onboarding timeouts, rebuilds the Kuma and PostgreSQL Go helpers, updates TorrServer libraries and adds source security reports. Use the [security remediation notes](SECURITY-REMEDIATION.md) and exact push runs on PR 2 to verify results. The branch remains a development candidate.
