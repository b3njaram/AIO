# Customer setup and handoff

Start with loopback-only bindings and complete setup locally (or via trusted SSH port forwarding). Do not put unconfigured applications on the internet. Customer uses their own credentials, hardware and authorized media. No account registration, email verification, CAPTCHA, third-party signups, or media acquisition is automated.

## Ports and data

With base port 18080: dashboard 18080, Jobbi Music 18081, Navidrome 18082, StreamHub 18083, Prowlarr admin 18084 (always loopback), Immich 18085, Nextcloud 18086, Vaultwarden 18087, Vikunja 18088, Pi-hole web 18089 and DNS 53 (optional), Uptime Kuma 18090. Use a different base port and name for every same-host pilot.

All paths below are under the specific instance directory, not under an existing personal installation. .env contains independent generated secrets and must stay private. Named volumes are per project. Nextcloud and databases use Docker-managed volumes, so put Docker's data disk on sufficient local SSD/storage or plan separate mounts before installation.

## First run

- Navidrome: open its UI first, create the initial admin using the username passed to --music-admin (default owner), then sign in to Jobbi Music with those credentials. Copy authorized audio to data/music; request a scan. Read-only library mount in this pilot. Peer downloading, remote import and shared filesystem deletion are not enabled. Native app source is pinned with the web code; customer-specific mobile app distribution, signed builds, server selection, offline caching isolation, CarPlay and Android Auto have not been certified. Start with the web experience.
- StreamHub: from repository root, run bash scripts/create-movie-user.sh /absolute/path/to/instance owner . Use a private password. Copy authorized videos into data/movies/media; in StreamHub, Community > Local media > Scan media folder. Test seek, full playback and watch history. TMDB account/API key is optional for basic local-media use; for catalog functionality obtain the customer's own key, respecting commercial terms. Prowlarr and TorrServer are scoped to this instance and optional integrations need manual approval. Set the customer's own API key in PROWLARR_API_KEY in the instance .env only if configuring a permitted source, and TMDB_API_KEY if applicable; apply with ctl.sh INSTANCE up -d backend frontend. External providers may require individual verification and terms. Do not reuse JobbiSoft credentials. No indexers are preconfigured.
- Immich: open the web UI and register initial owner locally, upload a test image and verify the phone backup app reaches the customer's HTTPS origin. Background thumbnails/face recognition can use substantial RAM/CPU; test on selected hardware.
- Nextcloud: finish setup using PostgreSQL preconfigured by Compose, create administrator, configure trusted domains, HTTPS and cron/background jobs according to upstream docs. Verify sync and file upload.
- Vaultwarden: HTTPS is mandatory for normal clients. Configure a customer HTTPS origin (VAULT_DOMAIN and dashboard URL), create/invite the owner using the admin interface and the instance-specific VAULT_ADMIN_TOKEN from the local .env, keep public signups disabled. Review upstream Argon2 admin-token guidance, configure SMTP if invites require it, and verify recovery/export before storing passwords. Disable administrative access when not needed.
- Vikunja: register the first owner in private, then disable registration by setting the compose environment VIKUNJA_SERVICE_ENABLEREGISTRATION to false in a customer-specific override before enabling remote access. Update public URL. Test create/edit/export.
- Uptime Kuma: create an admin privately; set up desired monitors. Dashboard probes are separate from Kuma.
- Pi-hole: only when explicitly selected on an isolated private LAN IP; confirm port 53 TCP/UDP and firewall before enabling. Use DNS_PASSWORD locally. Test a single client first; document how to restore the old DNS. Do not change router settings automatically or expose an open resolver.
- Tailscale: install the official client on the host using its distro instructions; customer authenticates in their own tailnet and approves devices. Do not reuse your personal tailnet or auth key. HTTPS and ACLs must be configured by customer/admin. If serving the dashboard through HTTPS, edit dashboard.json app url fields with the actual approved HTTPS origins and recreate dashboard. No public Funnel for media or credentials.

## Manage, verify, backup

    bash scripts/ctl.sh /absolute/path/to/instance ps
    bash scripts/verify.sh /absolute/path/to/instance
    bash scripts/ctl.sh /absolute/path/to/instance logs --tail=100
    mkdir -p /path/to/external-backup
    bash scripts/backup.sh /absolute/path/to/instance /path/to/external-backup

Backups stop this instance briefly; they include private credentials, media bind mounts and project volumes. Encrypt them and keep an off-device copy. Validate SHA256SUMS and rehearse recovery in a disposable VM, using the same app versions and a fresh instance/project name. Restore bind paths and named volumes only while services are stopped; review paths, ownership and credentials before restart. Do not restore into another active customer's volumes. RAID is not a backup. A scheduler and fully automated restore are not yet implemented.

## Acceptance tests before a paid delivery

Install a fresh instance on a supported host, create accounts and HTTPS origins, verify login/logout and permissions, test music and video end-to-end with sample media you own, photo upload, file sync, password manager, task app, DNS (if installed), remote access and dashboard. Measure idle and streaming watts at wall, CPU/RAM/disk and temperature. Run a backup and restore drill. Test a second instance with different ports and names, then stop/restart one and confirm the other and any pre-existing host service remain reachable. Check first-run admin access and no unauthorized cross-instance access. Test reboot and remote access from a separate device.

No automatic production upgrades. Review upstream releases and image digests, back up and test on staging before promoting. Recovery procedure and hardware-specific compatibility need validation. No promise that an upstream integration remains available forever.
