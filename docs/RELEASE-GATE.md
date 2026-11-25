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
