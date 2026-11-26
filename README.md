# Jobbi Home Server — AIO

Own your cloud. Stop renting it.

This repository separates the public quote site from customer deployments. It is a **pilot release**, not a certified production appliance. No changes to the existing Jobbi Music or StreamHub repositories or servers are required.

## Public quotation website

On a Linux Docker host:

    git clone https://github.com/b3njaram/AIO.git ~/docker/jobbi-aio
    cd ~/docker/jobbi-aio
    docker compose -p jobbi-quote -f quote/compose.yaml up -d --build
    curl -fsS http://127.0.0.1:8780/ | head

Set QUOTE_PORT or QUOTE_BIND in the environment if needed. The default is loopback port 8780. Switch ONLY the quote.jobbisoft.com.mx Cloudflare route after verifying the new page; retain the previous origin for rollback. If hosted by Cloudflare Pages, migrate the existing custom-domain association to the intended tunnel or deploy quote/ directly to Pages. See docs/QUOTE.md. No other hostname needs to change.

## Customer server

For a dedicated headless Ubuntu Server 24.04 LTS x86-64 appliance (including customer-specific USB seed generation), see [guided installation](docs/CUSTOMER-INSTALL.md). The new `scripts/setup-customer.py` previews by default and orchestrates package installation, preflight, provisioning, reachability and onboarding with `--apply`. Keep the customer stack loopback-only until account setup and private HTTPS are verified. Never execute the customer installer on the owner production host.

Recommended starting target: dedicated x86-64 Linux host or VM, Docker Engine + Compose v2, Git, Python 3, Bash, curl, 16 GB RAM for the full stack, and SSD for Docker databases. NAS-specific support and ARM compatibility are not yet validated. Format/mirror drives outside this installer. Confirm the mounted filesystem before installing.

    mkdir -p ~/jobbi-customers
    python3 scripts/install.py --name family1 --data-root ~/jobbi-customers --base-port 18080 --bind 127.0.0.1
    bash scripts/verify.sh ~/jobbi-customers/family1

Default applications: Jobbi Music/Navidrome, StreamHub, Immich, Nextcloud, Vaultwarden, Vikunja, Uptime Kuma and Tailscale instructions. Add Pi-hole with --apps and an explicit LAN bind only after checking DNS port 53. No Ollama. Choose a subset with --apps music,movies,photos,files,monitor,remote. Use --prepare-only to generate files and fetch code without starting services.

The dashboard at http://127.0.0.1:18080 lists selected services, HTTP reachability and filesystem usage. No Docker socket, no unified login, no public dashboard exposure. See docs/HANDOFF.md for account onboarding, media paths, HTTPS, backups and acceptance checks.

Each instance has a separate project name, network, named volumes, bind mounts and generated secrets. The host OS, Docker daemon, CPU, RAM, disks and power remain shared; use separate customer-owned systems or VMs for strong isolation. Existing project or port conflicts stop installation. Do not run down -v.

## Repository layout

- quote/: bilingual, regional quote/savings calculator, Docker image and compose.
- deploy/: commercial customer stack, dashboard and monitoring.
- scripts/: new-instance provisioning, instance control, StreamHub account creation, backup, status verification.
- docs/: deployment and handoff.

Jobbi Music and StreamHub use specific upstream commit SHAs, fetched into each new customer instance. Several third-party images still use version-family or latest tags; freeze and verify image digests for production releases. Existing deployments are not auto-updated. Treat paid support as separate from indefinite use of installed software; external accounts and content rights remain the customer's responsibility.

See upstream application licenses and distribution terms before shipping. Provide required notices and corresponding source where required. No copyrighted media or external account credentials are included.

The quote site can export a non-secret `jobbi-home-config.json` (application IDs, hardware preferences, and support period). Pass `--quote /path/to/jobbi-home-config.json` to the installer; it uses the selected apps unless overridden with `--apps`. Hardware and commercial pricing remain subject to manual validation. Pi-hole selection requires an explicit LAN IP.

## Business launch and release qualification

See [business launch playbook](business/PLAYBOOK.md), [intake](business/INTAKE.md), [proposed bilingual support terms](business/SUPPORT.md), [acceptance](business/ACCEPTANCE.md) and [quick start](business/QUICKSTART.md). The offline business/order.py calculator uses proposed prices and actual local costs. Never commit completed customer records to this public repository.

Run `python3 scripts/preflight.py --data-root /path/to/mounted/data --apps music,movies,photos,files,monitor` before installing. New installations snapshot their deployment files and source references under the instance directory; pulling AIO will not silently replace the installed Compose definition. First-run private LAN binding requires explicit --allow-private-bootstrap; localhost remains the default. To update a customer, plan and test a migration deliberately.

## Private procurement

[Jobbi Hardware Finder](business/sourcing/README.md) searches US/MX suppliers from one command, screens exact parts, exports a private HTML report and an editable review CSV, and selects a complete confirmed landed-cost BOM. No purchases are automated; optional eBay credentials and the pinned DealCompare checkout provide live eBay leads; prepared retailer links and explicitly authorized structured-data collection cover other suppliers without paid search. The public quotation site is unchanged.

## Client policy

[Supported customer clients](docs/CLIENTS.md): browser-first, compatible third-party apps, optional experimental native Jobbi source. Official app-store publishing and commercial signing are not launch requirements. No unsigned binary is represented as installable.

## Private owner dashboard

[Business dashboard setup](business/dashboard/README.md): hardware searches, confirmed landed BOM, costing, cash ledger, orders and warranty tracking. Localhost plus SSH forwarding; no public site changes.

## Customer operations

The private owner dashboard includes installation planning, support cases, expiry reminders and bilingual handoff drafts. [Maintenance guide](docs/MAINTENANCE.md) covers read-only diagnostics, opt-in cold backup scheduling and supervised updates/recovery. No unattended upgrade or deletion is enabled. Hardware qualification remains a real-device task.

## Development handoff

Current qualification evidence, open failures and the continuation checklist are in [the development tracker](docs/DEVELOPMENT-TRACKER.md).
