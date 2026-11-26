# syntax=docker/dockerfile:1
FROM golang:1.27.3-alpine@sha256:fa3d596898d9f126af7c01d14ee7597bab3f39cccf392ef36b69fe77cd681f18 AS healthcheck
ADD --checksum=sha256:d16fd78404ed92d7e8b61f535790f4f508d807d5d76c2d9fbb275e2cd86f3f9e https://raw.githubusercontent.com/louislam/uptime-kuma/5aa5dec425f8a955b54e150636979a6927745ec5/extra/healthcheck.go /src/healthcheck.go
RUN --network=none CGO_ENABLED=0 GOTOOLCHAIN=local go build -trimpath -o /out/healthcheck /src/healthcheck.go

# Keep the full upstream release, including browser monitoring and MariaDB.
FROM louislam/uptime-kuma:2.5.12@sha256:8e4b6bef96417ec98a35dc103c99cc64fc229a01e584e56d95d9004d2003c02a

# DLA-4932-1: signed Debian Bookworm security update. Exact package versions
# are intentional: fail closed if the repository no longer carries them.
# Do not downgrade, remove unrelated packages or use unsigned repositories.
RUN set -eu; \
    version='156.0.8078.108-1~deb12u1'; \
    . /etc/os-release; test "$VERSION_CODENAME" = bookworm; \
    printf '%s\n' 'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian-security bookworm-security main' > /tmp/jobbi-security.list; \
    apt-get -o Dir::Etc::sourcelist=/tmp/jobbi-security.list -o Dir::Etc::sourceparts=- -o Acquire::Retries=4 update; \
    set -- "chromium=$version" "chromium-common=$version"; \
    for pkg in chromium-sandbox chromium-driver chromium-l10n chromium-shell chromium-headless-shell; do \
      if [ "$(dpkg-query -W -f='${db:Status-Status}' "$pkg" 2>/dev/null || true)" = installed ]; then set -- "$@" "$pkg=$version"; fi; \
    done; \
    apt-get -o Dir::Etc::sourcelist=/tmp/jobbi-security.list -o Dir::Etc::sourceparts=- -o Acquire::Retries=4 install -y --no-install-recommends --no-remove "$@"; \
    for item in "$@"; do test "$(dpkg-query -W -f='${Version}' "${item%=*}")" = "$version"; done; \
    chromium --version; \
    rm -f /tmp/jobbi-security.list; rm -rf /var/lib/apt/lists/*

COPY --from=healthcheck --chmod=0755 /out/healthcheck /app/extra/healthcheck

# Same-major npm patch artifacts are verified against the exact upstream lock.
RUN --mount=type=bind,source=patch-npm.cjs,target=/tmp/jobbi-patch-npm.cjs,ro \
    --mount=type=bind,source=npm-security-patches.json,target=/tmp/jobbi-npm-plan.json,ro \
    node /tmp/jobbi-patch-npm.cjs /tmp/jobbi-npm-plan.json
