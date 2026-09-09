"""Fail closed on advisory lookup errors or known release dependency vulnerabilities."""
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen


def main():
    packages = json.loads(Path(sys.argv[1]).read_text())
    if not packages:
        raise SystemExit("No resolved dependencies to scan")
    findings = []
    for start in range(0, len(packages), 100):
        batch = packages[start:start + 100]
        payload = {"queries": [
            {"package": {"ecosystem": "Maven", "name": item["name"]}, "version": item["version"]}
            for item in batch
        ]}
        request = Request("https://api.osv.dev/v1/querybatch", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=60) as response:
            results = json.load(response)["results"]
        if len(results) != len(batch):
            raise SystemExit("Incomplete advisory response")
        for package, result in zip(batch, results):
            for vulnerability in result.get("vulns", []):
                findings.append(f'{package["name"]}@{package["version"]}: {vulnerability["id"]}')
    if findings:
        raise SystemExit("\n".join(findings))
    print(f"No known vulnerabilities in {len(packages)} resolved release Maven packages.")


if __name__ == "__main__":
    main()
