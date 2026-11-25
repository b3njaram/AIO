# Private JobbiSoft business dashboard

Uses the same eBay credentials, DealCompare virtualenv, saved reports and cash.sqlite3 as the CLI. No paid services. Never expose it through Cloudflare or public reverse proxy. Loopback only with generated password and same-origin POST protection. Use SSH forwarding over your private Tailscale connection; this version intentionally does not offer direct LAN binding.

On your server from AIO:

    bash business/dashboard/start.sh --init
    cat ~/.config/jobbi-business/dashboard-password
    bash business/dashboard/start.sh

Keep the password private. Browser username is owner. From your personal computer in another terminal:

    ssh -N -L 8790:127.0.0.1:8790 osvaldoramirez@macmini2012

Open http://127.0.0.1:8790 and sign in. Keep both terminals open. Forward the same local port because Host and Origin checks require it. Use a trusted personal computer. No direct public or Tailscale Serve reverse proxy in this version. For persistent operation install the optional user systemd service below.

    bash business/dashboard/install-service.sh
    systemctl --user status jobbi-business

If the server does not keep user services running after logout, use the foreground method or explicitly decide whether to enable user lingering. The installer does not change system-wide settings. To stop: systemctl --user stop jobbi-business. To update: git pull --ff-only then systemctl --user restart jobbi-business. Do not run both foreground and service on the same port.

Features: run free searches, browse previous reports, view candidates with optional eBay images (external request, disabled by default), compare supplier links and coverage, confirm actual offers including landed costs in two markets, calculate cheapest complete confirmed hardware configuration, transfer to profit calculator, save customer order references, record cash/refunds and track delivery/support/warranty. Other retailers remain manual search/confirmation unless separately authorized CLI collection is supported. No automatic purchase, no fake inventory, no direct supplier credentials. A new search captures images; old saved reports may not have them. All search prices are preliminary. Complete build covers catalog parts only, not additional required accessories or backup.

The dashboard stores private order details and confirmed offers in the existing cash.sqlite3 database using additive tables. No customer records belong in Git. Use customer reference/folio instead of sensitive personal details and never store passwords in notes. Cash totals are not profit. Warranty dates are indicative; mixed components require item-level records. Existing cash ledger is the primary source. To back up the ledger, stop the dashboard and use SQLite backup or copy a quiescent database into encrypted private storage. Sourcing reports are private too. Browser UI English initially. No installation execution, payment processing, warranty claims or support tickets yet. No production server or public quote change.
