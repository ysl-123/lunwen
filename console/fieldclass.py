"""从字段取值识别存储形态。不读取演示目录。"""

from __future__ import annotations

import re


def storage_algorithm(value: str) -> str | None:
    if value.startswith("sha256:"):
        return "SHA-256"
    if value.startswith("sm3:"):
        return "SM3"
    if value.startswith("aes-gcm:"):
        return "AES"
    if value.startswith("sm4:"):
        return "SM4"
    return None


def classify_storage(value: str) -> str:
    if value is None or value == "":
        return "unknown"
    algorithm = storage_algorithm(value)
    if algorithm in ("SHA-256", "SM3"):
        return "hash"
    if algorithm in ("AES", "SM4"):
        return "ciphertext"
    if re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return "hash"
    if value.startswith(("$2a$", "$2b$", "$2y$", "pbkdf2$", "scrypt$", "cipher:")):
        return "hash" if value.startswith(("$2a$", "$2b$", "$2y$", "pbkdf2$", "scrypt$")) else "ciphertext"
    if re.fullmatch(r"[A-Za-z0-9+/]{24,}={0,2}", value):
        return "ciphertext"
    return "plaintext"
