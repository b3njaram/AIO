# Optional private health reporting

Disabled by default. No public endpoint, remote commands, app credentials, or required subscription. The customer explicitly consents to sharing the same limited fields as the manual report. The owner registry accepts only authenticated fresh reports for that exact appliance and keeps only the latest report.

On the owner host, after reviewing the private tailnet ACL, using a matching customer-accessible private TLS hostname and owner-owned certificate/key:

    python3 business/dashboard/health-receiver.py --cert CERT --key KEY
    python3 business/dashboard/health-receiver.py --cert CERT --key KEY --apply

This is an optional independent receiver, NOT the owner admin port. Keep it running in a reviewed owner user service if desired. Never expose it using Funnel, public port forwarding, or an open proxy. The receiver has no read APIs, and requires a separate 90-day per-appliance credential. The customer and owner must agree on network access; no automatic changes to ACLs or device sharing.

In the authenticated Customers page, record explicit sharing consent, then issue a reporting credential. Copy it once via a secure channel; only its hash is stored. Never put the token in a URL, shell history, Git, or support notes. On the customer's appliance, as original non-root operator:

    python3 scripts/health-reporting.py INSTANCE enable --url https://OWNER.TAILNET.ts.net:17993/v1/health --appliance-id ID --apply
    python3 scripts/health-reporting.py INSTANCE send
    sudo python3 scripts/install-notification-service.py INSTANCE --operator OPERATOR --apply

The timer runs every 15 minutes; the sender connects only to verified tailnet address space with normal TLS hostname verification. The owner UI marks automatic reports stale after one hour. Revocation on either side stops future reporting (owner credential revocation rejects subsequent requests). To stop on customer host:

    python3 scripts/health-reporting.py INSTANCE disable --apply

Revoke reporting credential in Customers; revoke sharing to erase the currently stored report as well. Earlier private business backups may retain previous reports according to the agreed retention policy. Rotate credentials at expiry. Never interpret a missing report as proof the server is offline. Actual cross-tailnet ACL/TLS checks remain unperformed; do not expose the admin dashboard to customers to enable this feature.
