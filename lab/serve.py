"""按当前档位启动本机业务站点。只监听 127.0.0.1。"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address
from pathlib import Path

import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from lab.gm_channel import serve_forever
from lab.openssl_cli import CERT_DIR
from lab.store import DATA_DIR, entry_for, export_evidence, get_grade, init_db

HOST = "127.0.0.1"


def write_pid() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "lab.pid").write_text(str(os.getpid()), encoding="utf-8")


def ensure_rsa_cert() -> tuple[Path, Path]:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    key_path = CERT_DIR / "yi.key"
    crt_path = CERT_DIR / "yi.crt"
    if key_path.exists() and crt_path.exists():
        return crt_path, key_path
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, HOST)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(IPv4Address(HOST))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    crt_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return crt_path, key_path


def main() -> None:
    write_pid()
    init_db()
    export_evidence()
    grade = get_grade()
    if grade == "丙":
        uvicorn.run("lab.app.main:app", host=HOST, port=8000, log_level="info")
    elif grade == "乙":
        cert, key = ensure_rsa_cert()
        uvicorn.run(
            "lab.app.main:app",
            host=HOST,
            port=8443,
            ssl_certfile=str(cert),
            ssl_keyfile=str(key),
            log_level="info",
        )
    elif grade == "甲":
        from lab.pack import save_zip

        packed = save_zip()
        print(f"下载本次材料：{packed}")
        serve_forever()
    else:
        raise RuntimeError(f"未知档位 {grade}，入口 {entry_for(grade)}")


if __name__ == "__main__":
    main()
