#!/usr/bin/env bash
# Start the pinned optional stack on an isolated disposable bridge.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true ]]
root=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
export JOBBI_IV_FIXTURE=$work
ctl=(docker compose --project-name jobbi-invidious-fixture --file "$work/compose.json")
cleanup() {
    if [[ -f "$work/compose.json" ]]; then
        "${ctl[@]}" ps -a || true
        "${ctl[@]}" down --volumes || true
    fi
    rm -rf -- "$work"
}
trap cleanup EXIT
export PYTHONPATH="$root/scripts"
python - "$root/deploy/invidious-pilot.json" <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path
from pilot_media import invidious, invidious_credentials

work = Path(os.environ["JOBBI_IV_FIXTURE"])
source = work / "source"
pins = json.loads(Path(sys.argv[1]).read_text())
subprocess.run(["git", "init", "-q", str(source)], check=True)
subprocess.run(["git", "-C", str(source), "fetch", "--depth=1",
                "https://github.com/iv-org/invidious.git", pins["source_commit"]], check=True)
subprocess.run(["git", "-C", str(source), "checkout", "--detach", "FETCH_HEAD"], check=True)
if subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() != pins["source_commit"]:
    raise ValueError("Unexpected Invidious source")
cfg = invidious(work, pins["images"], source, invidious_credentials())
# Runtime startup requires outbound access for the upstream session.
# No host ports or customer credentials are used by this test.
for service in cfg["services"].values():
    if "build" in service:
        service["build"]["context"] = str(Path(sys.argv[1]).resolve().parent / "security-patches")
    service["restart"] = "no"
del cfg["services"]["invidious"]["ports"]
f = work / "compose.json"
with os.fdopen(os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
    json.dump(cfg, stream)
PY
"${ctl[@]}" up -d --build --wait --wait-timeout 180
wait_for_frontend() {
    for _ in {1..24}; do
        if "${ctl[@]}" exec -T invidious wget -q -T 5 -O /dev/null http://127.0.0.1:3000/; then
            return 0
        fi
        sleep 5
    done
    echo "Invidious did not serve its local homepage" >&2
    return 1
}
db() {
    "${ctl[@]}" exec -T invidious-db psql -XqAt -v ON_ERROR_STOP=1 -U invidious -d invidious "$@"
}
wait_for_frontend
test "$(db -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('users','playlists','videos')")" = 3
db -c 'CREATE SCHEMA jobbi_fixture; CREATE TABLE jobbi_fixture.persistence(id integer PRIMARY KEY); INSERT INTO jobbi_fixture.persistence VALUES (417);'

# Recreate every container while retaining project volumes. This exercises
# database and companion-cache mount persistence without provider accounts.
"${ctl[@]}" up -d --no-build --force-recreate --wait --wait-timeout 180
wait_for_frontend
test "$(db -c 'SELECT id FROM jobbi_fixture.persistence')" = 417
echo "PASS: pinned Invidious startup, initialized schema, and database persistence across container recreation."
