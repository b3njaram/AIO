# Hardware sourcing and qualification

## Preferred suppliers (candidate list, not an exclusive or verified reseller agreement)
US: Amazon.com (prefer manufacturer or authorized seller), Dell Refurbished, B&H, reputable business off-lease sellers. Mexico: Amazon.com.mx, Cyberpuerta, PCEL and local distributors. eBay only for vetted refurbished computers with clear returns; avoid anonymous used storage. No orders placed.

Compare exact landed cost, shipping, local taxes, import/customs costs where applicable, seller reliability, serial-based warranty, RMA region, restocking/return window, delivery lead time. Commercial imports must follow applicable declarations and duties; do not assume personal duty-free allowances apply. Retain supplier receipts privately. No claim that US component warranties transfer across borders or to a resale customer. Dell Refurbished states 100-day limited warranty; eligible Amazon Renewed listings generally 90 days. Check actual listing, return deadline and resale eligibility. IronWolf and WD Red Plus generally offer 3-year limited manufacturer warranties; check model and region before selling.

Sources:
- https://www.dellrefurbished.com/cms/limited-warranty/warranty/1.html
- https://www.aboutamazon.com/news/retail/amazon-renewed-like-new-products-with-a-guarantee
- https://www.seagate.com/support/internal-hard-drives/nas-drives/ironwolf/
- https://www.westerndigital.com/products/internal-drives/wd-red-plus-sata-3-5-hdd

## Proposed initial SKUs (hardware qualification required)
- BYOH: existing x86-64 Linux system, compatibility check, no supplied hardware warranty.
- Home Core: refurbished Intel 8th generation or newer i5-class business tower/SFF with 16 GB RAM, SSD for OS/db, new 4 TB NAS drive; separate backup recommended. Check exact drive bays, SATA power, cooling, NIC, BIOS support and iGPU capability. Do not assume hardware transcoding is supported by StreamHub.
- Home Family: same class, two new matching 4 or 8 TB NAS drives mirrored, separate backup recommended. Select case/NAS with actual internal bays and cooling.
- Home Plus: 32 GB RAM, more bays, custom quote only after capacity and load testing.

Micro desktops often need external drive enclosures; do not claim a USB enclosure provides reliable RAID or power-loss behavior before validating. Prefer internal SATA or a validated DAS for multiple drives. Do not market NAS models as supported until actual installation and recovery tests pass. New customer data drives only by default; clearly disclose refurbished compute and any used components. Never promise a specific simultaneous-stream count until measured.

## Procurement and burn-in
Obtain written scope and cash deposit only under agreed lawful terms; purchase hardware after any applicable cancellation period or legally valid customer instruction. Record actual serial, condition, warranty region and deadline. Check BIOS/firmware, memory, SMART, new-drive extended test, SSD health, CPU/load temperatures, network and sustained I/O. Non-destructive checks only on existing data. Test reboot, power recovery, backup and full playback on authorized test media. Measure idle and representative load with wall watt meter. Reject any failing unit. Keep one compatible loaner/spare only after demand justifies it.

Quote hardware using landed cost, warranty reserve, actual labor, travel and support. Recheck prices before promising availability. For the first few customers, build to order rather than stocking many drive sizes.
