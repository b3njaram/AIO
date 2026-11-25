# Jobbi Hardware Finder

One command searches both US and Mexico hardware markets, filters candidate suppliers, screens exact part numbers and condition, and produces a local HTML report and JSON. This is a procurement assistant, not checkout automation or a guarantee of the cheapest offer across the whole internet.

## Setup
Python 3.10+ only; no pip dependencies. Keep credentials in the shell or a private password manager; do not put them in GitHub, in reports or in the public quote site.

- SERPAPI_KEY: Google Shopping and optional targeted Google site search via https://serpapi.com/ . Check its current plan, quotas and commercial terms before enabling. Searches consume provider quota; --max-searches caps requests and --deep searches each named supplier separately. No automatic paid subscription or API key is created.
- EBAY_CLIENT_ID and EBAY_CLIENT_SECRET: optional existing official Browse API credentials from your DealCompare setup (do not copy its entire .env or expose secrets). Requires eBay approval. US marketplace only, delivery context El Paso by default. No eBay purchasing.
- Without credentials use --offline and verified CSV, or configure one provider; a missing provider is clearly reported. No direct retailer APIs are asserted. Amazon, Dell Refurbished, B&H, Cyberpuerta and PCEL are discovery sources through the indexed search provider, not individually guaranteed live inventory feeds. Coverage may be incomplete or unavailable.

## One-command run
From AIO:
 
    python3 business/sourcing/search.py --profile family --markets both --target MX --deep

Other profiles: core, family8, plus. The default deep run has 20 shopping/site calls for a two-part build across both markets; eBay calls are separate. The report saves to ~/.local/share/jobbi-business/sourcing/ and prints its exact path. Open the HTML locally or copy securely from the server; never expose it as a public site. If provider results are empty, report coverage honestly. Source prices are not final or authoritative.

## Ranking and final BOM
Indexed and eBay search prices are provisional. Unknown delivery is never zero. Currency can be inferred from search market but is not guaranteed, and search leads are never converted into a final BOM automatically. Variable listings, accessories, wrong form factors and used/recertified storage are flagged. For approved NAS drives we require the exact model and new condition; a 4 TB family build requires two identical drives. The tower is a candidate only: physical SATA bays and power connectors may differ by model/configuration; check dimensions/cooling, SSD/RAM and actual compatibility. All accessory, backup, power and shipping needs must be added manually to costing; the catalog is a starter candidate list, not a complete certified system.

Copy verified.example.csv to a private directory outside AIO. After checking a supplier's exact option, available stock, condition, model, warranty and compatibility, enter its unit cost, per-unit delivery, tax and import costs (explicit zero only when confirmed), market, currency, date and confirmed=yes. Set compatibility_checked=yes only after validating the item for the build. Allocate order-wide shipping or taxes per unit consistently. Check the warranty applies to the customer region. A confirmed offer must be no older than 3 days. Then run:

    python3 business/sourcing/search.py --profile family --target MX --offline --verified-csv ~/jobbi-private/verified.csv --fx 17.5

Replace the sample FX with the actual quote rate. Cross-border landed comparison requires explicit FX and all landed-cost fields; those fields must include lawful import costs for target market. The cheapest complete confirmed build chooses the lowest landed cost per component. No BOM if a required component is missing. Review the final order again and use business/order.py for labor, support, warranty, travel and margin. No actual orders are placed.

Provider references: https://serpapi.com/google-shopping-api ; https://serpapi.com/organic-results ; https://developer.ebay.com/develop/api/buy/browse_api/item/search .

The HTML report shows the lowest screened advertised candidate per market/component, separately from the final verified BOM. The generated review.csv pre-populates direct supplier links; confirm the exact listing and fill actual costs/quantity before re-importing. No API credentials are needed to review the report or calculate the final confirmed BOM. If using eBay-only, omit SERPAPI_KEY; results will be partial.
