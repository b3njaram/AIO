# Cash-only operating procedure

Owner direction: accept cash only, USD for US sales and MXN for Mexican sales. No online checkout, payment links, card fees, or recurring automatic billing. Business formation/invoicing project deferred by owner, not waived: before taking any actual sale, verify applicable registration, taxes, required receipts/invoices, customs and consumer obligations. Cash does not eliminate them. Texas Comptroller: https://comptroller.texas.gov/taxes/sales/ .

1. Agree itemized written scope, exact currency, hardware condition, warranty, cancellation rights, delivery and payment schedule. Give required notices and warranty before purchase.
2. For BYOH: proposed payment at completed delivery. For special-order hardware: proposed deposit up to actual landed hardware cost, only with agreed lawful cancellation/refund terms and after required cooling-off period or legally valid arrangement. No blanket nonrefundable deposit. Do not buy parts speculatively based on verbal acceptance.
3. Count and verify cash together in a safe agreed location. Record each deposit, balance, refund and change separately with unique transaction and order IDs. Provide signed cash acknowledgment; a cash acknowledgment is not a substitute for mandatory tax documentation. Do not publicly disclose cash-storage location or customer addresses.
4. At delivery confirm acceptance and collect remaining balance as agreed. Do not deny warranty based solely on missing original receipt if other proof of purchase exists.
5. Refund in original currency, record a separate transaction, obtain acknowledgment without waiving rights. Keep cash and records secure; reconcile daily and separate personal/business money.
6. Keep ledger and customer details outside GitHub; use an encrypted private location. Do not put any real order, serial, contact or payment record in this public repository. Never collect payment-card data.

For quotes use business/order.py with cash payment fee zero and explicit overhead for cash handling, travel, returns and warranty. Any tax collected is not revenue. For payments above thresholds or cross-border movements, verify applicable reporting and legal obligations; do not split payments to avoid reporting.

## Optional private ledger

Run from AIO on a trusted Linux machine. The default database is outside Git and created with restricted file permissions. Keep an encrypted backup. Use either the ledger or your private spreadsheet as the primary record, not both independently. Examples use fictional IDs and amounts:

    python3 business/records.py open DEMO001 MX 6500
    python3 business/records.py record TX001 DEMO001 deposit 4000
    python3 business/records.py record TX002 DEMO001 balance 2500
    python3 business/records.py show DEMO001
    python3 business/records.py totals

A refund is a separate entry; order cancellation or changes to the agreed total require a separate documented amendment. No accounting, tax, receipt issuance, inventory control, or customer data collection is automated. Cash totals are not profit. For actual sales retain all legally required records.
