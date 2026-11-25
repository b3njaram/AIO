# Supported customer clients — launch decision

The product is the customer-owned server, not an app-store subscription. No paid Apple developer membership or official native Jobbi Music app distribution is required for launch. The Jobbi Dashboard and the web applications remain the supported first-party experience. Native Jobbi builds are optional experiments, not part of the purchase promise.

| Service | Default client | Other options to validate |
| --- | --- | --- |
| Jobbi Music / Navidrome | Jobbi Music web UI | Subsonic-compatible clients (e.g. Amperfy on iOS, Symfonium on Android); connect to Navidrome, not the Jobbi frontend |
| StreamHub | Web browser | Browser on compatible TVs or connected devices; do not claim Plex/Jellyfin client compatibility |
| Immich | Immich web UI | Official Immich mobile app |
| Nextcloud | Browser | Official Nextcloud desktop and mobile clients |
| Vaultwarden | Private HTTPS web vault | Bitwarden clients with customer server URL |
| Vikunja | Browser | Browser shortcut if supported |
| Pi-hole / Uptime Kuma | Browser | Private administration only |
| Remote access | Customer-owned Tailscale | Official Tailscale client on supported devices |

Third-party apps may charge, have separate terms, require HTTPS or have limited feature parity. Verify the client's exact version and supported platform on real devices before promising it. Subsonic clients do not automatically provide Jobbi-specific social, importer or other custom features. Web shortcuts are not native offline apps; browser background playback and offline support vary.

For Navidrome use a separate private HTTPS origin connected to NAV_PORT. Keep the web login and API private to the customer's network/tailnet, do not expose the administration UI publicly. Use customer-owned accounts; no personal JobbiSoft URLs, API credentials or permanent access. See HANDOFF.md for private network setup.

Optional Jobbi native source preparation remains available (MOBILE.md). Android APKs must be signed to install, even if sideloaded; a local debug-signed build is not a production release. iOS IPAs require valid signing/provisioning and free-account sideloading can expire. Do not describe unsigned binaries as installable or lifetime mobile access. No signing or store submission is planned. If customers request an experimental build, explain requirements and limitations; keep signing materials private.

Customer acceptance: test the chosen browser and one requested third-party client, verify login/logout, upload or playback with authorized content, and verify remote access from a second device. Document actual working apps in the handoff. App store or native app certification is not a launch gate.
