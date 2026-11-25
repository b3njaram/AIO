# Jobbi Home pilot release gate

Release scope is the customer-owned x86-64 Linux appliance, browser-first, cash only, no mandatory recurring subscription. Native apps optional; no official signing or distribution. No external media catalogs, paid APIs or promised lifetime support. The public quote and owner dashboard are independent from each customer server.

## Evidence required

- AIO static checks: quote HTTP and assets under private checkout permissions; dashboard smoke.
- Customer pilot checks: full-stack startup; two project isolation; monitoring backup restore; authenticated StreamHub generated media login, byte range and full transfer, logout, recovery; task owner and closed registration checks; optional native feed disabled; Nextcloud WebDAV upload, retrieval, anonymous denial and restart persistence.
- Owner dashboard browser checks: synthetic hardware verification, landed BOM, costing, order, cash, installation plan, support, handoff and persistence.
- Review dependency and image versions, exact release manifest, customer source patch version and private port bindings. No unattended upgrades.
- Validate every selected service's actual login, upload/playback and recovery using authorized test data. HTTP-only checks do not count as functional acceptance.
- Verify private HTTPS and customer-owned remote access from a second device; no publicly accessible setup/registration. Actual wall power, temperature, capacity, performance, installation time, SMART, independent backups and reboot tests on the exact hardware.
- Deliver customer-approved terms, hardware-specific warranty, support scope, recovery training, legal disclosures and required receipts. Keep records private. Do not accept paid orders before applicable obligations are resolved.

## Pilot vs paid launch

CI success is software evidence only. A passing test at one revision does not certify later changes, hardware, full data recovery for every app, live supplier prices, or security. The owner must verify physical acceptance and customer-controlled credentials. Do not mark untested items complete. Use business/ACCEPTANCE.md and HARDWARE-QUALIFICATION.md.

The operator may continue developing AIO without modifying personal production repositories, buying hardware, creating subscriptions, enabling remote public access, or making customer commitments. Deploy only intentionally. Record actual release/test URLs and customer-specific version privately.

## Release candidate regression gate

The full pilot must pass at the exact candidate revision, not just the PR's short isolation-only workflow. Verify the full-stack, library-recovery, media-recovery, office-recovery, infrastructure-recovery and staged-upgrade job conclusions individually. Check static and owner-dashboard browser results too. The library pilot must confirm both public and private playlist changes using the pinned Navidrome version; the task pilot requires actual registration denial, login and task persistence. Do not revert security patches merely to make tests green. Physical hardware, customer-owned tailnet access, actual device clients and local business obligations remain manual acceptance gates.

## Appliance boot and customer UI gate

Require passing unit tests of seed generation and guard rules, all three UI browser suites, Docker preview regression, functional app setup/recovery, and the dedicated headless Ubuntu VM boot/missing-disk workflow at the proposed release. Validate the generated ISO through actual Subiquity interactive disk selection on a disposable VM and then boot the physical candidate. Use the private qualification evidence collector plus real measured wall power, thermal/load tests, backup restore, physical reboot, missing-disk behavior and second-device customer ACL/TLS verification. A VM pass is not a hardware pass. Do not create a stable commercial tag until those gates are satisfied.

For RAID1 configurations, additionally verify actual array assembly after reboot, degraded operation, replacement and resynchronization, expansion and independent restore on disposable storage before offering these operations commercially. Storage Manager preview is not evidence of successful physical disk operations.

The offline update trial must pass source-hold, isolated candidate startup, and rollback on disposable instances, and verify actual customer data and post-reboot service behavior before any commercial cutover. Never claim data-safe rollback if writes occurred on the candidate and were not reconciled.

## Independent runtime isolation audit
Run `python3 scripts/security-audit.py INSTANCE` against the running exact candidate. It checks expected services, actual loopback port mappings, container hardening, device access, project network membership, mounts, restart policy and registration/security environment flags without printing credentials. The full-stack and two-instance pilots must pass this check. A non-loopback DNS/LAN configuration is deliberately outside this audit and requires separate network qualification. This is not a vulnerability scan or an external TLS/ACL test.

## Image vulnerability and license gate
The `Exact release image security scan` workflow builds the pinned customer stack in a disposable runner, creates stopped containers and scans actual local image IDs with a checksum-pinned official Trivy archive (v0.76.2; verify the official release and digest again when updating). All high, critical and unknown-severity findings, including those with no fix, require review. Missing scanner data, failure to fetch the vulnerability database, or timeout is not a pass. The local `scripts/scan-release.py INSTANCE --output PRIVATE_NEW_DIRECTORY` also works with a separately verified scanner. The report contains package versions and license names; it is not a full SBOM or proof of legal compliance. Before commercial distribution, independently verify upstream exact-version license texts, copyright notices, dependency obligations, source availability requirements, and branding permissions. Never treat the scanner's detected licenses as sufficient evidence of commercial distribution rights. Do not disable vulnerability checks merely to get green CI.

## Exact revision readiness report
Run `python3 scripts/release-readiness.py FULL_COMMIT_SHA` (optionally provide a read-only GitHub token through the GITHUB_TOKEN environment variable, not the command line). It checks completed push/dispatch jobs for static, full application, browser/Docker, ISO, VM, RAID and image scan workflows. Skipped jobs, mismatched commits, newer failures and unavailable API evidence do not count. Trigger skipped workflows explicitly for the intended revision. The report always leaves commercial approval false: physical acceptance and distribution/legal review are separate. It never publishes or tags a release.

A commit with `[release-gate]` schedules all seven workflows on the same revision, regardless of which files changed. The missing-disk VM drill retains the UUID checks, uses stable virtual PCI slots, and captures guest mount/daemon diagnostics on failure. The data mount is an explicit required and ordered dependency even when its unit uses nofail for normal OS boot. Do not classify a failed reattachment as a successful power-loss test.

## Initial scan findings and remediation
The scan at `0166293a` reported 2,366 high/critical/unknown package findings across 18 distinct images (findings can repeat across images and packages; this is not a count of distinct exploitable vulnerabilities). Major concentrations were Uptime Kuma (943), Nextcloud (372), Immich database (293), Immich server (249), Vaultwarden (199), Immich ML (91), Valkey (76), Navidrome (54) and the PostgreSQL group (28). The runtime build hardening in patch version 5 removes unused package managers from local application images and removes StreamHub compilation tools after installation; it pins the Node 22 base and tests native SQLite loading. The dashboard uses only the Python standard library, so unused Python package managers and libraries are removed. Older exact-image restores retain their original patch version. These changes require fresh scan and functional regression evidence. Third-party findings remain unresolved until reviewed or remediated with supported releases and compatibility checks; no vulnerability suppression or blanket acceptance is authorized.

## Development continuation while hardware is unavailable
Physical qualification is deferred at the project owner's request so later development can proceed. This is a development assumption, not evidence of passing physical tests or authorization to sell. Retain physical, private-network, software security and commercial blockers explicitly. No stable commercial release until the actual gates are satisfied.
