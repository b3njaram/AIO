"""Scan committed release inputs and publish location-only findings for review."""
import argparse
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path


def locations(scan):
    results = []
    for section in scan.get("Results", []):
        for group, id_field in (("Secrets", "RuleID"), ("Misconfigurations", "ID"), ("Vulnerabilities", "VulnerabilityID")):
            for item in section.get(group) or []:
                results.append({
                    "category": group, "rule": item[id_field], "file": section["Target"],
                    "line": item.get("StartLine") or (item.get("CauseMetadata") or {}).get("StartLine"),
                    "package": item.get("PkgName"), "severity": item.get("Severity", "UNKNOWN"),
                })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scanner", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source"
        source.mkdir()
        archive = root / "source.tar"
        subprocess.run(["git", "archive", "-o", archive, sha], check=True)
        with tarfile.open(archive) as tar:
            tar.extractall(source, filter="data")
        raw = root / "results.json"
        subprocess.run([str(args.scanner.resolve()), "fs", "--scanners", "vuln,secret,misconfig",
                        "--format", "json", "--output", raw, "."], cwd=source, check=True)
        data = json.loads(raw.read_text())
        if not isinstance(data.get("Results"), list) or not data["Results"]:
            raise ValueError("Source scan returned no coverage")
        rows = locations(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"commit": sha, "findings": rows}, indent=2))
    # Do not emit matched text, secrets, code snippets or the raw report.
    print(len(rows), "source findings. Inspect the location-only artifact.")
    return bool(rows)


if __name__ == "__main__":
    raise SystemExit(main())
