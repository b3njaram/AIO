# Private HTTPS on a customer-owned tailnet

Do not use the owner's personal Tailscale account, Cloudflare tunnel, DNS or public domains. Enroll the dedicated customer host in their own tailnet, enable MagicDNS/HTTPS certificates with their consent, and restrict access to approved customer devices/users via tailnet policy. Certificate names may be public in certificate transparency logs; choose a non-identifying device name. Do not use Funnel, publicly reachable ports, or open routers.

Official documentation: https://tailscale.com/docs/reference/tailscale-cli/serve and https://tailscale.com/docs/features/tailscale-serve.

## Preview
Install using loopback binds; complete local onboarding via SSH tunnel first, except remote access and Vaultwarden's HTTPS-dependent acceptance. Before enabling the password route, verify signups are disabled and the owner invitation is intended; complete its login/recovery checks after HTTPS. On the customer host:

    python3 scripts/private-access.py INSTANCE

The tool checks local Tailscale enrollment, exact .ts.net hostname, customer instance identity, onboarding confirmation, loopback binds, disjoint ports and absence of existing Serve/Funnel config. It prints independent HTTPS URLs, proposed non-secret env and dashboard changes, and per-port enable/disable commands. It does not modify files, Docker, Tailscale, ACLs, or public DNS. Existing Serve/Funnel rules are refused, not reset. Choose an unused --https-base if necessary.

## Prepare app origins before exposing
Keep private copies of .env and dashboard.json and do not print or send credentials. Apply only the listed non-secret environment keys to the existing .env and the proposed URL fields in dashboard.json. For Vikunja, confirm the frozen compose file actually honors TASK_REGISTRATION=false and verify signup is closed. For Jobbi Music, secure cookies require HTTPS after this change. For Vaultwarden, set the exact HTTPS DOMAIN and invite the customer privately. For Nextcloud, configure the precise host:port as a trusted domain, HTTPS overwrite protocol and trusted proxy address based on the actual proxy connection; consult upstream docs. Do not trust wildcard proxies. Verify all apps individually, including Immich upload and sync, Navidrome clients, StreamHub cookies/ranges and Vikunja login. Some clients may not support custom ports; test on the promised client. Do not reuse a personal origin. Apply changed application environment using ctl.sh INSTANCE up -d for only the corresponding services, and recreate dashboard after editing its config. Do not expose unfinished accounts.

Once the customer approved the tailnet ACL and first-run setup, run only the generated Serve commands on their dedicated server, one at a time. Review status after each command. Tailscale may require interactive consent; no automation bypasses it. Stop on any failure, disable only routes created for this installation and keep unrelated settings unchanged. The preview does not use --yes or reset.

    python3 scripts/private-access.py INSTANCE --verify

Checks expected HTTPS listener and proxy mapping, and rejects public Funnel flags; does not prove ACL or application security. Test from a separate approved customer device using actual TLS verification, and verify denial from an unauthorized device/account outside the tailnet. Do not use curl -k. Verify reboots and native client compatibility. Revoke temporary installer access. Record final URLs and acceptance evidence privately. Disable routes using the generated per-port off commands only; do not reset the tailnet. Revert app origin configuration only after the routes are disabled.

This is an operator-guided private access workflow, not unattended enrollment or a certified HTTPS deployment. Actual Tailscale and customer device tests are required.

## Operator-controlled apply and rollback

On a dedicated customer host, finish the local accounts and review the preview. Obtain customer approval for the ACL and service interruption. Run the following from the reviewed AIO checkout:

    python3 scripts/private-access.py INSTANCE --prepare-origins

This saves the original files privately inside the instance and replaces only the origin settings and dashboard links. Recreate the dashboard and selected affected application containers with `bash scripts/ctl.sh INSTANCE up -d --force-recreate --no-deps --no-build --pull never dashboard`, appending only the installed affected service names (jobbi-music, vaultwarden, vikunja). Complete the app-specific Nextcloud proxy/trusted-domain setup separately. Check the frozen deployment and verify that each customer app is ready for private access.

    python3 scripts/private-access.py INSTANCE --enable-routes
    python3 scripts/private-access.py INSTANCE --verify

The local operator needs permission to manage Tailscale Serve. The tool checks running backend owners, port bindings and critical environment flags. It journals the plan, adds HTTPS listeners one by one and verifies the resulting configuration. If a command fails or is interrupted, run the rollback from that instance. Stop and review any unexpected configuration reported by verification.

    python3 scripts/private-access.py INSTANCE --rollback-routes
    python3 scripts/private-access.py INSTANCE --rollback-origins

Recreate the same app containers after restoring origin files. Configuration changes made after preparation are reported for manual reconciliation. Confirm TLS, session cookies, login and access denial from actual client devices.

## Guided apply / rollback

After customer-owned Tailscale enrollment, verified first-run accounts, customer-approved ACLs and the intended Vaultwarden invitation, run `python3 scripts/finish-private-access.py INSTANCE` to preview. Add --apply to journal the origins, set exact Nextcloud trusted host and HTTPS canonical URLs, recreate affected app containers, configure the expected Serve routes and verify them. On failure it attempts scoped rollback; use --rollback for a deliberate reversal. Existing custom Nextcloud trusted proxy settings require manual review; the wizard never trusts broad proxy networks. Test actual device TLS, ACL denial and application login separately. First boot installs the official signed Tailscale package for the remote profile but does not enroll the machine or enable Funnel. The customer retains account and ACL control.

## Native Pi-hole admin access
The private-access planner now accepts the native loopback DNS profile and can configure its administrative web interface over customer-owned Serve. The TCP/UDP DNS listener remains local and is not tunneled through an HTTPS reverse proxy. DNS client activation and tailnet DNS settings remain separate and require customer approval. No automatic changes to routes, router, DHCP, or DNS settings. Experimental Invidious instances still require canonical origin migration before a tailnet transition. This extends the existing technician-controlled route transaction; it is not a completed browser-based LAN-to-tailnet cutover.
