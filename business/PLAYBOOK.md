# Jobbi Home — launch playbook (draft for owner approval)

## Offer

Own your cloud. Stop renting it. Sell a configured customer-owned appliance and the work of installing, testing, teaching and maintaining it. No mandatory Jobbi subscription, no remote kill switch, no hosted commercial media catalog. The installed versions remain usable subject to hardware, compatibility and upstream terms. Internet, electricity, media purchases, disks, repairs and external services are separate. Do not promise lifetime updates, uninterrupted remote access or equivalence to Netflix/Spotify catalogs.

Start with a paid pilot only after the technical release gate passes. Offer one standardized x86-64 platform (16 GB RAM, SSD for OS and databases, separate data disks, wired Ethernet), then a 32 GB upgrade after validation. Start with customer-owned Linux hardware or a built-to-order machine; don't advertise Synology or ARM support until tested. RAID1 is optional, not backup. Quote actual tested hardware, not estimated compatibility. No data recovery guarantee. Never sell a preloaded unauthorized media library.

## Proposed regional launch rates (not approved or live prices)

| Service | El Paso USD | Ciudad Juárez MXN |
|---|---:|---:|
| Bring your own compatible hardware, setup + 6 months limited support | 249 | 2,999 |
| Additional six months included at purchase | 49.50 | 599.50 |
| Optional annual maintenance | 99 | 1,199 |
| Premium annual support (scope quoted separately) | 179 | 1,999 |
| Out-of-scope hourly service | 49 | 499 |

Hardware is separate: actual landed local cost + proposed 12% markup (not 12% net margin). Taxes, shipping, travel, cash handling costs, warranty reserve, labor and support reserve must be included in internal costing; do not treat taxes collected as revenue. Use local supplier invoices/FX at order time. Requote if quote expires or components change. Prices are proposals and may be too low on complex jobs. Never accept an order below the contribution floor without owner review.

Use the private costing helper: `python3 business/order.py --help`. No customer data, passwords, payment details or completed order records belong in this public repository.

## Workflow

1. Inquiry: use the intake template. Find actual monthly bills, data size, users, devices and network; explain what self-hosting replaces and what it does not.
2. Compatibility: confirm disk layout, power, wired network, upload speed, OS, hardware, app selection, HTTPS and backup destination. Reject unsupported or unsafe builds.
3. Quote: calculate actual parts, labor, support allowance, transport, fees and warranty provision; confirm currency, taxes, expiry and scope. Confirm business registration, invoicing/tax and warranty obligations for the sale location with a qualified local adviser before accepting payment.
4. Order: written acceptance and mutually agreed deposit/return terms before buying special-order parts. Suggested deposit only covers agreed nonrecoverable procurement, subject to consumer law and payment terms. Accept cash only; follow CASH-SALES.md. No payment provider integration.
5. Assemble: record serials and supplier warranties privately, check SMART/drive health and temperatures, install OS security updates and Docker, measure real power. Do not erase existing disks without documented owner approval and backup.
6. Provision: new isolated instance, fresh credentials, local-only first boot, customer enters external accounts. No personal JobbiSoft tokens. Run acceptance checklist, backup/restore and security tests.
7. Deliver: transfer admin and recovery information securely, verify customer has ownership and backups, remove temporary support access, collect acceptance and remaining payment under agreed terms. Give invoice and quick-start guide in preferred language.
8. Support: start clock at signed delivery. Log support minutes and issues privately; obtain explicit consent for every remote session. No permanent admin access by default. Offer maintenance renewal before expiry without locking the appliance.

## Pilot milestones

- Gate A: CI passes syntax, independent instances, backup smoke and authenticated media smoke; no unresolved critical security issues.
- Gate B: dedicated spare Linux machine with full stack, actual phones/TV browsers, reboot, backup restore, HTTPS, network isolation, measured power. NAS validation separately.
- Gate C: one consenting pilot household, signed scope and handoff, actual install/support time captured; fix issues before offering to strangers.
- Gate D: first three paid orders, review actual margin, support minutes and returns; only then broaden hardware catalog.

Suggested launch channels: personal referrals, local small-business and family networks, demos using your own authorized content. No unsolicited mass messaging, no paid ads before validating conversion. Track leads, quotes, conversions, actual installation minutes, support minutes, gross contribution and refunds. Target 3 pilot inquiries, 1 successful install, then 3 paid orders. These are targets, not forecasts.

## Pending owner decisions

Legal seller and invoicing setup deferred, but applicable obligations must be confirmed before sales; supplier agreements and verified hardware; approval of drafted warranty/return terms; service address and support hours; travel charges, support cap and price floor. Cash-only is decided. Official email verified in CONTACT.md. Review terms with appropriate advisers before taking orders. No registration, payment account, or real sales transaction is created by this repository.

See SOURCING.md, WARRANTY-RETURNS.md, CASH-SALES.md, CONTACT.md and the blank trackers. The proposed warranty is separate from optional support.
