# syntax=docker/dockerfile:1
FROM scratch AS npm_archives
ADD --checksum=sha256:48c903f98c5591d8d26f16f389d5cb3435459474c645209a79f6241bf4b657b6 https://registry.npmjs.org/postcss-selector-parser/-/postcss-selector-parser-7.1.6.tgz /archives/48c903f98c5591d8d26f16f389d5cb3435459474c645209a79f6241bf4b657b6.tgz
ADD --checksum=sha256:df3454ef205791ce50b5b9241762dcf9bfe1aa9f7f01d3057229be7dac0c2dc3 https://registry.npmjs.org/ws/-/ws-8.21.3.tgz /archives/df3454ef205791ce50b5b9241762dcf9bfe1aa9f7f01d3057229be7dac0c2dc3.tgz
ADD --checksum=sha256:696942c2a488c9d7428e9ca5f12ccf03b52de01dcdbfe4d4751d392f0491ae16 https://registry.npmjs.org/lodash/-/lodash-4.18.1.tgz /archives/696942c2a488c9d7428e9ca5f12ccf03b52de01dcdbfe4d4751d392f0491ae16.tgz
ADD --checksum=sha256:7d28c9a3ef17ce542093c78ec191481503e2711d29db1bd1522062303ab40478 https://registry.npmjs.org/minimatch/-/minimatch-9.0.9.tgz /archives/7d28c9a3ef17ce542093c78ec191481503e2711d29db1bd1522062303ab40478.tgz
ADD --checksum=sha256:6f4d64fdab4cdc5096d48537f35a6bbb2b8b918abaa4bdb0833e92486f66befc https://registry.npmjs.org/brace-expansion/-/brace-expansion-2.1.7.tgz /archives/6f4d64fdab4cdc5096d48537f35a6bbb2b8b918abaa4bdb0833e92486f66befc.tgz
ADD --checksum=sha256:697b463be3cdbd9ffc8f4194fd5019a69ddf95875fb703d78b2b115cc9e740a8 https://registry.npmjs.org/picomatch/-/picomatch-4.0.7.tgz /archives/697b463be3cdbd9ffc8f4194fd5019a69ddf95875fb703d78b2b115cc9e740a8.tgz
ADD --checksum=sha256:13411b6b3bb984844bd04eba6543a5adf22c1e8749f721dc2d56af4339ba93a4 https://registry.npmjs.org/ip-address/-/ip-address-10.7.5.tgz /archives/13411b6b3bb984844bd04eba6543a5adf22c1e8749f721dc2d56af4339ba93a4.tgz
ADD --checksum=sha256:a071d8840d37b4541c2efecb225023f825c983b43968c08d9f96dc1baaa33b5d https://registry.npmjs.org/jsonata/-/jsonata-2.2.1.tgz /archives/a071d8840d37b4541c2efecb225023f825c983b43968c08d9f96dc1baaa33b5d.tgz
ADD --checksum=sha256:df0241b3046b505d27396da6eef107f14dffb108f77aa89cfd9611a928eb6dfe https://registry.npmjs.org/protobufjs/-/protobufjs-7.6.6.tgz /archives/df0241b3046b505d27396da6eef107f14dffb108f77aa89cfd9611a928eb6dfe.tgz
ADD --checksum=sha256:0c0cf3a6d15d7649fa843ab2f5991f5857bc7515d48ae8c35aa5addaf6e5fcdd https://registry.npmjs.org/axios/-/axios-0.34.0.tgz /archives/0c0cf3a6d15d7649fa843ab2f5991f5857bc7515d48ae8c35aa5addaf6e5fcdd.tgz
ADD --checksum=sha256:18b75cb9c66c8c08bab5cacccd09013c31d3182f1e001c19d8815c5bb46e0802 https://registry.npmjs.org/glob/-/glob-10.5.0.tgz /archives/18b75cb9c66c8c08bab5cacccd09013c31d3182f1e001c19d8815c5bb46e0802.tgz
ADD --checksum=sha256:e4df4beb99eb51d606a03ba3e07879ca320dffcad029edd9ae63876e0df773f2 https://registry.npmjs.org/qs/-/qs-6.16.2.tgz /archives/e4df4beb99eb51d606a03ba3e07879ca320dffcad029edd9ae63876e0df773f2.tgz

FROM golang:1.27.3-alpine@sha256:fa3d596898d9f126af7c01d14ee7597bab3f39cccf392ef36b69fe77cd681f18 AS healthcheck
ADD --checksum=sha256:d16fd78404ed92d7e8b61f535790f4f508d807d5d76c2d9fbb275e2cd86f3f9e https://raw.githubusercontent.com/louislam/uptime-kuma/5aa5dec425f8a955b54e150636979a6927745ec5/extra/healthcheck.go /src/healthcheck.go
RUN --network=none CGO_ENABLED=0 GOTOOLCHAIN=local go build -trimpath -o /out/healthcheck /src/healthcheck.go

# Keep the full upstream release, including browser monitoring and MariaDB.
FROM louislam/uptime-kuma:2.5.12@sha256:8e4b6bef96417ec98a35dc103c99cc64fc229a01e584e56d95d9004d2003c02a

# DLA-4932-1 and DLA-4941-1: signed Debian Bookworm security updates. Exact package versions
# are intentional: fail closed if the repository no longer carries them.
# Do not downgrade, remove unrelated packages or use unsigned repositories.
RUN set -eu; \
    version='156.0.8078.108-1~deb12u1'; \
    . /etc/os-release; test "$VERSION_CODENAME" = bookworm; \
    printf '%s\n' 'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian-security bookworm-security main' > /tmp/jobbi-security.list; \
    apt-get -o Dir::Etc::sourcelist=/tmp/jobbi-security.list -o Dir::Etc::sourceparts=- -o Acquire::Retries=4 update; \
    pam='1.5.2-6+deb12u3'; \
    set -- "chromium=$version" "chromium-common=$version"; \
    for pkg in libpam-modules libpam-modules-bin libpam-runtime libpam0g; do \
      if [ "$(dpkg-query -W -f='${db:Status-Status}' "$pkg" 2>/dev/null || true)" = installed ]; then set -- "$@" "$pkg=$pam"; fi; \
    done; \
    for pkg in chromium-sandbox chromium-driver chromium-l10n chromium-shell chromium-headless-shell; do \
      if [ "$(dpkg-query -W -f='${db:Status-Status}' "$pkg" 2>/dev/null || true)" = installed ]; then set -- "$@" "$pkg=$version"; fi; \
    done; \
    apt-get -o Dir::Etc::sourcelist=/tmp/jobbi-security.list -o Dir::Etc::sourceparts=- -o Acquire::Retries=4 install -y --no-install-recommends --no-remove "$@"; \
    for item in "$@"; do test "$(dpkg-query -W -f='${Version}' "${item%=*}")" = "${item#*=}"; done; \
    chromium --version; \
    rm -f /tmp/jobbi-security.list; rm -rf /var/lib/apt/lists/*

COPY --from=healthcheck --chmod=0755 /out/healthcheck /app/extra/healthcheck

# glob 10.5.0 adds package-json-from-dist. The pinned image already has
# the exact compatible version 1.0.1 in its npm tree; reuse the identical
# local dependency rather than installing a new dependency graph.
RUN set -eu; \
    src=/usr/local/lib/node_modules/npm/node_modules/package-json-from-dist; \
    dst=/app/node_modules/redbean-node/node_modules/glob/node_modules/package-json-from-dist; \
    node -e 'const p=require(process.argv[1]+"/package.json"); if(p.name!=="package-json-from-dist"||p.version!=="1.0.1"||Object.keys(p.dependencies||{}).length)process.exit(1)' "$src"; \
    test -d "$src"; test ! -L "$src"; test -z "$(find "$src" -type l -print)"; \
    test ! -e "$dst"; test ! -L "$dst"; mkdir -p "$(dirname "$dst")"; \
    cp -a "$src" "$dst"; \
    chown -R --reference=/app/node_modules/redbean-node/node_modules/glob "$dst"

# Same-major npm patch artifacts are verified against the exact upstream lock.
RUN --network=none --mount=type=bind,from=npm_archives,source=/archives,target=/archives,ro \
    --mount=type=bind,source=patch-npm.cjs,target=/tmp/jobbi-patch-npm.cjs,ro \
    --mount=type=bind,source=npm-security-patches.json,target=/tmp/jobbi-npm-plan.json,ro \
    node /tmp/jobbi-patch-npm.cjs /tmp/jobbi-npm-plan.json

HEALTHCHECK --interval=60s --timeout=30s --start-period=180s --retries=5 CMD ["/app/extra/healthcheck"]
