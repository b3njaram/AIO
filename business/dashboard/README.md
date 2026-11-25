# Private JobbiSoft business dashboard

Uses the same eBay credentials, DealCompare virtualenv, saved reports and cash.sqlite3 as the CLI. No paid services. Never expose it through Cloudflare or public reverse proxy. Loopback only with generated password and same-origin POST protection. Use SSH forwarding or an explicitly allowed private Tailscale Serve origin. The server never listens on LAN or public interfaces.

On your server from AIO:

    bash business/dashboard/start.sh --init
    cat ~/.config/jobbi-business/dashboard-password
    bash business/dashboard/start.sh

Keep the password private. Browser username is owner. From your personal computer in another terminal:

    ssh -N -L 8790:127.0.0.1:8790 osvaldoramirez@macmini2012

Open http://127.0.0.1:8790 and sign in. Keep both terminals open. Forward the same local port because Host and Origin checks require it. Use a trusted personal computer. Never configure a public reverse proxy. For private Serve, see below. For persistent operation install the optional user systemd service below.

    bash business/dashboard/install-service.sh
    systemctl --user status jobbi-business

If the server does not keep user services running after logout, use the foreground method or explicitly decide whether to enable user lingering. The installer does not change system-wide settings. To stop: systemctl --user stop jobbi-business. To update: git pull --ff-only then systemctl --user restart jobbi-business. Do not run both foreground and service on the same port.

Features: run free searches, browse previous reports, view candidates with optional eBay images (external request, disabled by default), compare supplier links and coverage, confirm actual offers including landed costs in two markets, calculate cheapest complete confirmed hardware configuration, transfer to profit calculator, save customer order references, record cash/refunds and track delivery/support/warranty. Other retailers remain manual search/confirmation unless separately authorized CLI collection is supported. No automatic purchase, no fake inventory, no direct supplier credentials. A new search captures images; old saved reports may not have them. All search prices are preliminary. Complete build covers catalog parts only, not additional required accessories or backup.

The dashboard stores private order details and confirmed offers in the existing cash.sqlite3 database using additive tables. No customer records belong in Git. Use customer reference/folio instead of sensitive personal details and never store passwords in notes. Cash totals are not profit. Warranty dates are indicative; mixed components require item-level records. Existing cash ledger is the primary source. To back up the ledger, stop the dashboard and use SQLite backup or copy a quiescent database into encrypted private storage. Sourcing reports are private too. Browser UI English initially. No installation execution, payment processing, warranty claims or support tickets yet. No production server or public quote change.

New operations tabs: installation wizard generates copyable/downloadable commands for a dedicated customer host and saves plans by order. It never executes remote installs. Support cases track support/warranty/return/maintenance status, reminders show upcoming recorded expirations, and handoff downloads English/Spanish plain-text drafts. These are local records, not email/SMS alerts or legal documents. Diagnostics and backup runner are in docs/MAINTENANCE.md; customer execution requires operator approval.

## Private business data backup

On the owner host, mount an independent encrypted backup filesystem with access restricted to you, then run:

    python3 business/dashboard/backup-records.py /path/to/mounted/private-backups

Uses SQLite's online backup API so the dashboard need not stop. Runs integrity and foreign key checks and writes a SHA-256 checksum in a fresh directory. It refuses the same filesystem and does not overwrite or delete existing backups. This covers the cash database, orders, cases, saved plans and verified offers, not historical sourcing reports, password or API credentials. Back up reports separately if needed, and maintain credentials in your password manager. Actual independent filesystem and encryption must be verified. To recover, verify the checksum and inspect the database on a separate machine; stop the dashboard, keep a copy of the current DB and its WAL/SHM files, and follow a reviewed SQLite recovery procedure rather than overwriting a live ledger. 

### Recover a ledger copy

    python3 business/dashboard/backup-records.py /private/new-recovery --restore-from /mounted/backups/jobbi-business-TIMESTAMP

Uses a new private directory, verifies the copied bytes and SQLite integrity and foreign keys, then publishes cash.sqlite3. Review synthetic or real order totals locally before separately scheduling any cutover.

### Customer PDF documents

Install the distribution package `python3-reportlab` for the dashboard interpreter. In Support & handoff, choose the saved order, English or Spanish, and the document type. Receipts require the specific recorded payment or refund. The acceptance form leaves findings and signatures for the customer and technician. PDFs are generated in memory and downloaded by the authenticated owner.

## Private Tailscale preview (no SSH forwarding)

Keep the backend on 127.0.0.1 and explicitly allow the browser origin. For the isolated preview on port 8791:

    HOME="$HOME/.jobbi-preview" "$HOME/.jobbi-preview/venv/bin/python" business/dashboard/server.py --port 8791 --allow-origin http://macmini2012:8791

In another terminal on the owner host, first inspect `tailscale serve status` and `tailscale funnel status`. Use unused preview ports only. Do not reset unrelated routes or enable Funnel. If the preview ports are not already configured, run:

    sudo tailscale serve --bg --http=8791 http://127.0.0.1:8791
    sudo tailscale serve --bg --http=8781 http://127.0.0.1:8781

The second route needs the quote preview listening on 127.0.0.1:8781. On a permitted tailnet device visit http://macmini2012:8791 or http://macmini2012:8781. MagicDNS and tailnet ACL access must be enabled. Add the exact full .ts.net browser origin with a second --allow-origin if needed. HTTPS Serve is preferable for actual private financial records (use the exact https://name.tailnet.ts.net origin and matching HTTPS listener). HTTP preview traffic is carried through the encrypted Tailscale connection, but the browser does not consider the page an HTTPS secure context. Basic authentication and exact Host/Origin matching remain enforced; no forwarded headers are trusted. If a proxy rewrites Host, access fails closed. Restrict tailnet ACLs to owner devices. Never publish the business dashboard through Funnel or Cloudflare.

## No-login UI demo

For convenience on port 8791 only, append `--preview-no-auth` to the isolated preview command. This uses a new separate .jobbi-no-login-demo directory inside the selected HOME. Existing preview and real ledger records remain unchanged. Live hardware sourcing is disabled; do not enter customer or financial records. Anyone permitted by your tailnet ACL to reach this port can access the demo, so never enable Funnel or a public proxy. Exact Host and Origin checks remain active. Ordinary dashboard invocations still require credentials.

For the quote preview, use `bash quote/preview.sh` instead of a foreground Python HTTP server. It keeps the separate loopback backend running after logout and checks readiness without touching the live quote container. See docs/QUOTE.md.

## Detached Docker previews

Stop the old foreground preview processes (ports 8781 and 8791) once. From the preview checkout, as your normal Linux account, run `bash scripts/preview.sh`. It starts both separate Docker projects with restart policies, checks local health and retains demo records from the earlier no-login preview in ~/.jobbi-preview/.jobbi-no-login-demo. Only that directory is mounted into the admin container; no actual business credentials, ledger, home directory, or Docker socket are mounted. The container runs with your unprivileged UID/GID, read-only root and no capabilities. Both published ports are loopback-only; existing private Tailscale Serve mappings still apply. Use `bash scripts/preview.sh status`, `logs`, or `stop`. To update, fetch/switch the preview worktree and rerun `bash scripts/preview.sh`. Never expose these demo ports publicly. Docker must be running; automatic restart after reboot depends on the Docker service being enabled.
