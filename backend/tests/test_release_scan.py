from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import pytest


@pytest.mark.parametrize("payload,cleartext,success", [
    (b"clean application data", "false", True),
    (b"NeuroXDemo!2026", "false", False),
    (b"http://10.0.2.2:8000/", "false", False),
    (b"eyJabcdefghijk.abcdefghijk.abcdefghijk", "false", False),
    (b"clean application data", "true", False),
])
def test_release_gate_rejects_unsafe_artifacts(tmp_path, payload, cleartext, success):
    apk = tmp_path / "fixture.apk"
    manifest = tmp_path / "AndroidManifest.xml"
    with ZipFile(apk, "w") as archive:
        archive.writestr("classes.dex", payload)
    manifest.write_text(
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
        f'<application android:allowBackup="false" android:usesCleartextTraffic="{cleartext}" />'
        '</manifest>'
    )
    script = Path(__file__).resolve().parents[2] / "scripts/check_release_apk.py"
    result = subprocess.run([sys.executable, str(script), str(apk), str(manifest)], capture_output=True)
    assert (result.returncode == 0) == success
