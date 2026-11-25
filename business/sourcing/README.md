# Jobbi Hardware Finder — no paid search API

No SerpAPI, no paid search subscription. The eBay collector uses the actual pinned DealCompare checkout (commit 7cf8b54f13eac82816e3363363ed7ae43e84dc28), its official Browse API, 10-minute cache and price-variation screening. The private checkout is separate from your existing DealCompare install; no changes are made there.

## Install

From AIO on Linux (GitHub SSH access to your private DealCompare repo is required):

    bash business/sourcing/setup-dealcompare.sh
    mkdir -p ~/.config/jobbi-business
    chmod 700 ~/.config/jobbi-business
    umask 077
    nano ~/.config/jobbi-business/sourcing.env
    chmod 600 ~/.config/jobbi-business/sourcing.env

Enter the production App ID and Cert ID as plain key/value lines:
    
    EBAY_CLIENT_ID=your_production_app_id
    EBAY_CLIENT_SECRET=your_production_cert_id

No shell sourcing needed; the loader only accepts those two keys. Existing environment variables take precedence. Never commit credentials. No OAuth user token or sandbox key. eBay developer permissions and quotas apply.

    ~/.local/share/jobbi-business/sourcing-venv/bin/python business/sourcing/search.py --profile family --markets both --target MX

The report has eBay live leads (US marketplace only; postal-specific delivery not established), links for all suppliers, screening, review.csv, and a confirmed landed-cost BOM. Without credentials no automated eBay request is made unless --allow-ebay-html is explicitly enabled with authorization. API denial does not fall back to HTML. DealCompare does not provide Amazon, Dell, B&H, Cyberpuerta or PCEL APIs, nor unattended Facebook access. No fabricated inventory. All retailer search links are generated automatically, with exact model and site-specific search. Retailers without a permitted provider require a final manual lookup/confirmation. There is no guarantee of comprehensive free automatic retailer inventory.

Optional experimental direct collection: only if you have confirmed supplier permission for automated public search, repeat --authorized-retailer 'B&H' (or exact supplier name from catalog.json). It checks robots.txt, uses a normal identified request, reads in-stock JSON-LD Product/Offer data only, pauses between requests, and stops for robots exclusions, access challenges, errors or unreadable results. No direct Dell search route is implemented. Amazon and other retailers may prohibit or block automated collection; no evasion or permission assumption. --max-searches limits these attempts (robots requests are additional). The normal report does not fetch retailer sites. --deep is retained for compatibility, but all supplier links are always generated. No automatic purchases.

## Confirm the final build

Copy generated review.csv (or verified.example.csv) outside GitHub. Fill exact model, new drive condition, available quantity, per-unit price, shipping, tax, import costs, warranty, compatibility_checked=yes, confirmed=yes, and checked_date (within three days). Add manually verified offers from other suppliers as rows. For a mirrored build, two identical new drives are required. Exact tower bays, SATA power, cooling, memory and SSD still need hardware qualification. Unknown cost is not zero. Cross-border purchases must use actual applicable import costs, currency and regional warranty.

    python3 business/sourcing/search.py --profile family --target MX --offline --verified-csv ~/jobbi-private/verified.csv --fx 17.5

Replace example FX with actual quote rate. Confirmed BOM chooses cheapest complete combination among confirmed offers. Other accessories, backup, labor, overhead and warranty reserve must be included separately in business/order.py. Private reports are saved outside Git. No API calls in offline mode. Live API results have not been verified with your credentials.

Provider docs: https://developer.ebay.com/develop/api/buy/browse_api/item/search .
