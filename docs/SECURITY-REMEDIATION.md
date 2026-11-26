# Exact-image security remediation

The [43a838b scan](https://github.com/b3njaram/AIO/actions/runs/45763697446) finished with 1,624 high/critical/unknown package findings (499 reported fixes and 1,125 without a reported fix). The full Chromium patch removed 412 findings from the preceding 2,036. These are summed findings, not unique CVEs or proof of exploitability. All eight other push workflows on that revision passed.

## Next candidate: targeted OS packages

The same upstream application images remain pinned by digest. The following derived images apply package updates from signed stable OS repositories. Package floors are taken from the prior scanner report. No app database migration, entrypoint replacement, service removal, or scanner exclusion is involved. On Debian, resolve only signed official repositories in the same codename, prohibit removals and downgrades, and verify each resulting package version. On Alpine, preserve the upstream stable repository configuration, refuse edge, preserve all installed package names and verify each floor. A missing or incompatible fix fails the build. A newer compatible distro package can satisfy the floor, so build inputs alone do not promise bit-for-bit reproducibility. Exact built image IDs and archives remain the recovery authority.

| Service | Target |
| --- | --- |
| navidrome | pcre2, musl, musl-utils, libexpat, mbedtls, libcrypto3, libssl3, gnutls, curl, libcurl, zlib |
| immich-redis | musl, musl-utils, zlib |
| pihole | libxml2 |
| immich-db | libperl5.36, perl, perl-base, perl-modules-5.36, libssl3, openssl, dirmngr, gnupg, gnupg-l10n, gnupg-utils, gpg, gpg-agent, gpg-wks-client, gpg-wks-server, gpgconf, gpgsm, gpgv, libsqlite3-0, libxslt1.1, libpcre2-8-0, apt, libapt-pkg6.0, libgnutls30, libgssapi-krb5-2, libk5crypto3, libkrb5-3, libkrb5support0, libcap2, ca-certificates, liblzma5, xz-utils, tzdata |
| immich-server | apt, libapt-pkg7.0, libzstd1, login.defs, passwd, zlib1g, libgssapi-krb5-2, libk5crypto3, libkrb5-3, libkrb5support0 |
| immich-machine-learning | apt, libapt-pkg7.0, libzstd1, login.defs, passwd, zlib1g |
| nextcloud | libzstd1, login.defs, passwd |

The full release gate is requested for this candidate. The actual improvement must be measured from the new exact-image scan. If a package floor is unavailable, do not weaken it; verify the distro advisory and the signed repository or choose a supported upstream release. The remaining app dependencies, Go static binaries, upstream package families and findings without fixes require separate review. In particular, do not substitute a Debian PostgreSQL client for PGDG without compatibility tests, swap OpenEXR ABI packages in Immich, or remove Chromium/MariaDB from Kuma to lower counts. Never publish a stable commercial release based on a reduced finding count alone.

## Regression and evidence

All new derived images must retain the prior app version and function through authenticated pilots and exact backup/restore, staged upgrade and offline install. The scan groups findings by exact built image ID, records SBOMs and produces remediation.json. Review security results for both removed and newly introduced findings. Builds that use package floors should retain and distribute the exact reviewed image archives (not rebuild on a customer system to reproduce an approved release). No customer data or credentials enter CI.
