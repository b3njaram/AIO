#!/usr/bin/env bash
# Package only committed pilot source, independent of workstation credentials.
set -euo pipefail
out=${1:?Specify a new output directory}
root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
revision=$(git -C "$root" rev-parse --verify HEAD)
mkdir -- "$out"
cd -- "$out"
name="jobbi-home-pilot-$revision"
git -C "$root" archive --format=tar --prefix="$name/" "$revision" | gzip -n > "$name.tar.gz"
python3 - "$revision" "$name" <<'PY'
import json,sys
from pathlib import Path
commit,name=sys.argv[1:]
Path("release.json").write_text(json.dumps({"schema":1,"channel":"development","commit":commit,
    "archive":name+".tar.gz","contents":"tracked AIO source","commercial_release_approved":False},indent=2)+"\n")
PY
sha256sum "$name.tar.gz" release.json > SHA256SUMS
sha256sum --check SHA256SUMS
