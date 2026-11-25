# Customer setup and handoff

Start with loopback-only bindings and complete setup locally (or via trusted SSH port forwarding). Do not put unconfigured applications on the internet. Customer uses their own credentials, hardware and authorized media. No account registration, email verification, CAPTCHA, third-party signups, or media acquisition is automated.

## Ports and data

With base port 18080: dashboard 18080, Jobbi Music 18081, Navidrome 18082, StreamHub 18083, Prowlarr admin 18084 (always loopback), Immich 18085, Nextcloud 18086, Vaultwarden 18087, Vikunja 18088, Pi-hole web 18089 and DNS 53 (optional), Uptime Kuma 18090. Use a different base port and name for every same-host pilot.

All paths below are under the specific instance directory, not under an existing personal installation. .env contains independent generated secrets and must stay private. Named volumes are per project. Nextcloud and databases use Docker-managed volumes, so put Docker's data disk on sufficient local SSD/storage or plan separate mounts before installation.

## First run

- Navidrome: open its UI first, create the initial admin using the username passed to --music-admin (default owner), then sign in to Jobbi Music with those credentials. Copy authorized audio to data/music; request a scan. Read-only library mount in this pilot. Peer downloading, remote import and shared filesystem deletion are not enabled. Native app source is pinned with the web code; customer-specific mobile app distribution, signed builds, server selection, offline caching isolation, CarPlay and Android Auto have not been certified. Start with the web experience.
- StreamHub: from repository root, run bash scripts/create-movie-user.sh /absolute/path/to/instance owner . Use a private password. Copy authorized videos into data/movies/media; in StreamHub, Community > Local media > Scan media folder. Test seek, full playback and watch history. TMDB account/API key is optional for basic local-media use; for catalog functionality obtain the customer's own key, respecting commercial terms. Prowlarr and TorrServer are scoped to this instance and optional integrations need manual approval. After Prowlarr initializes, run python3 scripts/connect-movies.py /absolute/path/to/instance to link that instance's generated internal API key without copying it manually. Configure TMDB_API_KEY in its own .env if applicable; apply with ctl.sh INSTANCE up -d backend frontend. External providers may require individual verification and terms. Do not reuse JobbiSoft credentials. No indexers are preconfigured.
- Immich: open the web UI and register initial owner locally, upload a test image and verify the phone backup app reaches the customer's HTTPS origin. Background thumbnails/face recognition can use substantial RAM/CPU; test on selected hardware.
- Nextcloud: finish setup using PostgreSQL preconfigured by Compose, create administrator, configure trusted domains, HTTPS and cron/background jobs according to upstream docs. Verify sync and file upload.
- Vaultwarden: HTTPS is mandatory for normal clients. Configure a customer HTTPS origin (VAULT_DOMAIN and dashboard URL), create/invite the owner using the admin interface and the instance-specific VAULT_ADMIN_TOKEN from the local .env, keep public signups disabled. Review upstream Argon2 admin-token guidance, configure SMTP if invites require it, and verify recovery/export before storing passwords. Disable administrative access when not needed.
- Vikunja: new AIO deployments default to closed registration. Run python3 scripts/task-owner.py INSTANCE USERNAME EMAIL locally to create the owner; verify actual login and that registration is blocked. The pinned CLI takes the password as an argument, visible transiently to trusted local process/Docker admins. Older instances need separate review and must disable registration before remote access. Update public URL. Test create/edit/export.
- Uptime Kuma: create an admin privately; set up desired monitors. Dashboard probes are separate from Kuma.
- Pi-hole: only when explicitly selected on an isolated private LAN IP; confirm port 53 TCP/UDP and firewall before enabling. Use DNS_PASSWORD locally. Test a single client first; document how to restore the old DNS. Do not change router settings automatically or expose an open resolver.
- Tailscale: install the official client on the host using its distro instructions; customer authenticates in their own tailnet and approves devices. Do not reuse your personal tailnet or auth key. HTTPS and ACLs must be configured by customer/admin. If serving the dashboard through HTTPS, edit dashboard.json app url fields with the actual approved HTTPS origins and recreate dashboard. No public Funnel for media or credentials.

## Manage, verify, backup

    bash scripts/ctl.sh /absolute/path/to/instance ps
    bash scripts/verify.sh /absolute/path/to/instance
    bash scripts/ctl.sh /absolute/path/to/instance logs --tail=100
    mkdir -p /path/to/external-backup
    bash scripts/backup.sh /absolute/path/to/instance /path/to/external-backup

Backups stop this instance briefly; they include private credentials, media bind mounts and project volumes. Encrypt them and keep an off-device copy. Validate SHA256SUMS and rehearse recovery in a disposable VM, using the same app versions and a fresh instance/project name. Restore bind paths and named volumes only while services are stopped; review paths, ownership and credentials before restart. Do not restore into another active customer's volumes. RAID is not a backup. An opt-in scheduler and isolated recovery tool are available; see MAINTENANCE.md and the recovery section below.

## Acceptance tests before a paid delivery

Install a fresh instance on a supported host, create accounts and HTTPS origins, verify login/logout and permissions, test music and video end-to-end with sample media you own, photo upload, file sync, password manager, task app, DNS (if installed), remote access and dashboard. Measure idle and streaming watts at wall, CPU/RAM/disk and temperature. Run a backup and restore drill. Test a second instance with different ports and names, then stop/restart one and confirm the other and any pre-existing host service remain reachable. Check first-run admin access and no unauthorized cross-instance access. Test reboot and remote access from a separate device.

No automatic production upgrades. Review upstream releases and image digests, back up and test on staging before promoting. Recovery procedure and hardware-specific compatibility need validation. No promise that an upstream integration remains available forever.

## Version and business release controls

New installs copy deploy/ into instance/deployment and record release.json. ctl.sh uses this snapshot, not the repository's current Compose file. Old instances without a snapshot retain the legacy fallback with a warning. Do not overwrite the snapshot during a normal git pull. Backups now include it and release.json when present. Source checkouts are recreated from pinned references, not included in backups; store the exact source/release artifacts separately for long-term recovery. Full recovery still requires a tested migration and compatible images.

Before any paid installation, complete business/ACCEPTANCE.md and use business/PLAYBOOK.md. Run preflight against the actual data mount. --allow-private-bootstrap is only for a physically isolated/trusted private network; do not use it on a public or shared guest network. Do not advertise private HTTPS, automated remote access, or full support until verified on the selected hardware.

## Guided first-run setup

    python3 scripts/onboard.py /absolute/path/to/instance
    python3 scripts/onboard.py /absolute/path/to/instance --create-movie-owner owner
    python3 scripts/onboard.py /absolute/path/to/instance --link-movie-key
    python3 scripts/onboard.py /absolute/path/to/instance --mark movies

Only mark a step after actual functional validation. This tracker stores no passwords and does not claim automatic external account enrollment, HTTPS configuration, or app registration. Initial account creation remains customer-controlled for most services.

## Isolated restore pilot

Use only your own trusted cold backups; checksums detect corruption, not malicious edits. New backups contain the frozen deployment and release manifest. Use the same OS architecture and installation UID/GID and compatible image versions. The tool verifies all hashes, rejects unsafe archive paths and unsupported links, requires a fresh instance/project and distinct ports, restores files and project-scoped volumes, and leaves services stopped.

    python3 scripts/restore.py /path/to/backup --data-root /path/to/mounted/data --name recovery1 --base-port 19080
    bash scripts/ctl.sh /path/to/mounted/data/recovery1 up -d
    bash scripts/verify.sh /path/to/mounted/data/recovery1

The original remains untouched. Keep recovered copy loopback-only; never run it against the original production hostname. DNS restores, archives with bind-tree symlinks, external mounts, different UID/GID and legacy backups without a deployment snapshot need manual recovery. Some application volume layouts may contain unsupported links. Image tags are not all immutable; store compatible images separately and validate real application restore. This is a pilot, not a disaster-recovery guarantee.

For the browser-first and optional native client policy, see CLIENTS.md. Use private HTTPS endpoints on the customer's own network. No official Jobbi native app signing or distribution is planned.

Commercial source patch version 2 disables the personal native Android release feed. Existing instances are not automatically patched; release.json determines the patch version used in recovery. No change is made to the upstream personal repositories.

For an operator-guided private HTTPS plan and per-port Tailscale Serve verification, see PRIVATE-ACCESS.md. Use the customer-owned tailnet and do not enable Funnel.
