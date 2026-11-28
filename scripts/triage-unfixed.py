"""Join each no-fix finding to its installed SBOM component and Debian release advisory."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
from urllib.parse import quote


def triage(directory, tracker_file):
    report = json.loads((directory / "report.json").read_text())
    tracker = json.loads(tracker_file.read_bytes())
    rows = []
    for image in report["images"]:
        sbom = json.loads((directory / image["sbom"]).read_text())
        components = sbom["components"]
        os_version = next((c.get("version", "") for c in components
                           if c["type"] == "operating-system" and c["name"] == "debian"), "")
        suite = {"12": "bookworm", "13": "trixie"}.get(os_version.split(".")[0])
        packages = {}
        for component in components:
            if component.get("purl", "").startswith("pkg:deb/debian/"):
                properties = {p["name"]: p["value"] for p in component.get("properties", [])}
                packages[(component["name"], component["version"])] = properties.get(
                    "aquasecurity:trivy:SrcName", component["name"])
        for finding in image["vulnerabilities"]:
            if finding["fixed"]:
                continue
            advisory = finding["id"]
            source = packages.get((finding["package"], finding["installed"]))
            releases = tracker.get(source, {}).get(advisory, {}).get("releases", {})
            record = releases.get(suite, {})
            rows.append({**finding, "image": image["image"], "services": image["services"],
                         "source_package": source, "suite": suite, "vendor_status": record.get("status", "unmatched"),
                         "suite_fixed_version": record.get("fixed_version"), "vendor_note": record.get("nodsa_reason"),
                         "other_suite_fixes": {k: v["fixed_version"] for k, v in releases.items()
                                               if k != suite and v.get("fixed_version") not in (None, "0")},
                         "advisory": "https://security-tracker.debian.org/tracker/" + quote(advisory, safe="")
                         if releases else "https://osv.dev/vulnerability/" + quote(advisory, safe="")})
    with tracker_file.open("rb") as stream:
        tracker_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"release": report["release"], "scan_time": report["at"], "tracker_sha256": tracker_hash, "counts": dict(collections.Counter(
            row["vendor_status"] for row in rows)), "findings": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("tracker", type=Path)
    args = parser.parse_args()
    result = triage(args.evidence, args.tracker)
    (args.evidence / "unfixed-review.json").write_text(json.dumps(result, indent=2))
    print(len(result["findings"]), "unfixed findings reviewed against vendor data", result["counts"])
