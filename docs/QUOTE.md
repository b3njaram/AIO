# Quote site cutover

1. Clone AIO and start the quote-only Compose project (README). The public quote site never needs access to customer data or the customer stack.
2. Check curl -fsS http://127.0.0.1:8780/ and open it in a desktop and mobile browser. Select both markets independently of English/Spanish, change storage/mirror/apps, adjust electricity rate and verify the totals.
3. Find the current origin in Cloudflare. The prior response showed a Cloudflare cache HIT, but does not identify Pages versus Tunnel. Record the current route and any Pages custom-domain association before changing anything.
4. If cloudflared runs on this Linux host, set ONLY quote.jobbisoft.com.mx to http://127.0.0.1:8780. If cloudflared runs in Docker, loopback is that container, not the host; use a dedicated shared Docker network and quote:80, or an explicitly reachable private host IP. If using Pages, remove its custom-domain association only when ready to cut over and configure the new Tunnel hostname. Do not modify music, movie, or other DNS entries.
5. Purge the cached URL, not the entire zone. Check curl -fsS https://quote.jobbisoft.com.mx/ and verify the new page title. Roll back by restoring the previous route/association.

Future updates:

    cd ~/docker/jobbi-aio
    git pull --ff-only
    docker compose -p jobbi-quote -f quote/compose.yaml up -d --build

Pricing is in quote/app.js. USD and MXN rates are illustrative; verify local actual rates, hardware supplier quotations, currency exchange, and local subscription prices before accepting orders. The 12% hardware markup is not net profit; tax, labor, warranty, payment fees and support costs must be budgeted separately. The quote is not a payment or ordering backend.

Customers can download their service configuration as JSON; it contains no secrets or authoritative pricing. The installer accepts it via --quote.
