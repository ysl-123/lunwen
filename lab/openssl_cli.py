"""只调用固定的 openssl 参数，用来生成和校验 SM2 实验证书。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERT_DIR = ROOT / "lab" / "data" / "certs"


def openssl_exe() -> str:
    found = shutil.which("openssl")
    if found:
        return found
    candidate = Path(sys.base_prefix) / "Library" / "bin" / "openssl.exe"
    if candidate.exists():
        return str(candidate)
    raise RuntimeError("未找到 openssl")


def openssl_conf() -> str:
    candidate = Path(sys.base_prefix) / "Library" / "ssl" / "openssl.cnf"
    if candidate.exists():
        return str(candidate)
    return ""


def run_openssl(args: list[str], input_bytes: bytes | None = None) -> bytes:
    env = os.environ.copy()
    conf = openssl_conf()
    if conf:
        env["OPENSSL_CONF"] = conf
    proc = subprocess.run(
        [openssl_exe(), *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace")[-400:]
        raise RuntimeError(detail.strip() or "openssl 执行失败")
    return proc.stdout


def ensure_sm2_cert() -> tuple[Path, Path]:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    key = CERT_DIR / "jia.key"
    crt = CERT_DIR / "jia.crt"
    if key.exists() and crt.exists():
        text = describe_cert(crt.read_bytes())
        if "SM2-with-SM3" in text:
            return crt, key
    run_openssl(
        [
            "req",
            "-x509",
            "-newkey",
            "sm2",
            "-sm3",
            "-keyout",
            str(key),
            "-out",
            str(crt),
            "-days",
            "365",
            "-nodes",
            "-subj",
            "/CN=127.0.0.1",
        ]
    )
    return crt, key


def describe_cert(pem: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as tmp:
        tmp.write(pem)
        name = tmp.name
    try:
        return run_openssl(["x509", "-in", name, "-noout", "-text"]).decode("utf-8", "replace")
    finally:
        os.unlink(name)


def sm2_encrypt(cert_pem: bytes, payload: bytes) -> bytes:
    if "SM2-with-SM3" not in describe_cert(cert_pem):
        raise RuntimeError("证书签名不是 SM2-with-SM3")
    with tempfile.TemporaryDirectory() as folder:
        cert = Path(folder) / "cert.pem"
        pub = Path(folder) / "pub.pem"
        src = Path(folder) / "plain.bin"
        dst = Path(folder) / "wrapped.bin"
        cert.write_bytes(cert_pem)
        src.write_bytes(payload)
        run_openssl(["x509", "-in", str(cert), "-pubkey", "-noout", "-out", str(pub)])
        run_openssl(["pkeyutl", "-encrypt", "-pubin", "-inkey", str(pub), "-in", str(src), "-out", str(dst)])
        return dst.read_bytes()


def sm2_decrypt(payload: bytes) -> bytes:
    _crt, key = ensure_sm2_cert()
    with tempfile.TemporaryDirectory() as folder:
        src = Path(folder) / "wrapped.bin"
        dst = Path(folder) / "plain.bin"
        src.write_bytes(payload)
        run_openssl(["pkeyutl", "-decrypt", "-inkey", str(key), "-in", str(src), "-out", str(dst)])
        return dst.read_bytes()
