"""Regression gate for demo credentials, server URLs, and token/private-key literals."""
import re
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

FORBIDDEN = [
    rb"NeuroXDemo!2026", rb"maya@neurox\.demo", rb"anita@neurox\.demo",
    rb"https?://10\.0\.2\.2", rb"development-only-change-me",
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
]

with ZipFile(sys.argv[1]) as apk:
    for entry in apk.infolist():
        content = apk.read(entry)
        if any(re.search(pattern, content) for pattern in FORBIDDEN):
            raise SystemExit(f"Forbidden credential/server/token literal in {entry.filename}")
print("Release APK literal scan passed.")

manifest = ET.parse(sys.argv[2]).getroot()
application = manifest.find("application")
if application is None:
    raise SystemExit("Missing release application manifest")
namespace = "{http://schemas.android.com/apk/res/android}"
for attribute in ("usesCleartextTraffic", "allowBackup"):
    if application.get(namespace + attribute) != "false":
        raise SystemExit(f"Release {attribute} must be false")
if application.get(namespace + "debuggable", "false") != "false":
    raise SystemExit("Release must not be debuggable")
print("Release manifest security checks passed.")
