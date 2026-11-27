# syntax=docker/dockerfile:1
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
RUN --mount=type=bind,source=patch-npm.cjs,target=/tmp/jobbi-patch-npm.cjs,ro \
    --mount=type=bind,source=npm-security-patches.json,target=/tmp/jobbi-npm-plan.json,ro \
    node /tmp/jobbi-patch-npm.cjs /tmp/jobbi-npm-plan.json
