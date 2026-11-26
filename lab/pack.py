"""把当前档的证据打成压缩包。只给演示网站自己用。"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from lab.store import DATA_DIR, EVIDENCE_DIR, export_evidence, get_grade

REQUIRED = (
    "profile.json",
    "rows.json",
    "login_summary.json",
    "cert_summary.json",
    "config_export.json",
)


def zip_bytes() -> bytes:
    export_evidence()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED:
            archive.write(EVIDENCE_DIR / name, arcname=name)
    return buffer.getvalue()


def save_zip() -> Path:
    payload = zip_bytes()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"材料-{get_grade()}.zip"
    path.write_bytes(payload)
    return path
