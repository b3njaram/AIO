# Phase 9 — customer delivery

Generate a private, customer-specific quick-start and recovery draft from the installed dashboard and exact release, in English or Spanish:

    python3 scripts/customer-delivery.py INSTANCE --lang en --output ~/private-home-guide.md
    python3 scripts/customer-delivery.py INSTANCE --lang es --output ~/private-home-guia.md

The generator uses approved private HTTPS app origins only, leaves unresolved addresses for review, excludes arbitrary configuration fields and secrets, and does not mark any acceptance checkbox complete. Review every address and deliver privately. Never include passwords or recovery keys. Use the owner dashboard's existing order, installation, warranty, cash record and handoff PDF tools for transaction-specific documents. Issue any legally required invoice/receipt separately.

Recovery training: demonstrate the existing backup catalog, checksum verification, encrypted export/import and strict exact-image restore on an isolated candidate. Keep the source instance untouched. Record the independent backup location and recovery key custody privately; provide the customer with the exact tested release and operator documentation. Explain that a backup checksum is not proof of successful restore. Do not use private support credentials as recovery keys. See MAINTENANCE.md, STORAGE.md, HANDOFF.md and business/ACCEPTANCE.md.

The generated guide is not a warranty, sales contract, receipt or signed acceptance. Keep actual measured hardware and network acceptance separate.