"""演示用的存储变换。丙明文，乙为 SHA-256 与 AES-GCM，甲为 SM3 与 SM4。"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AES_KEY = bytes.fromhex("00112233445566778899aabbccddeeff")
SM4_KEY = bytes.fromhex("0123456789abcdeffedcba9876543210")


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sm3_text(text: str) -> str:
    return "sm3:" + hashlib.new("sm3", text.encode("utf-8")).hexdigest()


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def aes_gcm_encrypt(text: str) -> str:
    nonce = os.urandom(12)
    blob = nonce + AESGCM(AES_KEY).encrypt(nonce, text.encode("utf-8"), None)
    return "aes-gcm:" + _b64(blob)


def aes_gcm_decrypt(stored: str) -> str:
    raw = _unb64(stored.removeprefix("aes-gcm:"))
    nonce, blob = raw[:12], raw[12:]
    return AESGCM(AES_KEY).decrypt(nonce, blob, None).decode("utf-8")


def _pkcs7(data: bytes, block: int = 16) -> bytes:
    pad = block - (len(data) % block)
    return data + bytes([pad]) * pad


def _unpad(data: bytes) -> bytes:
    pad = data[-1]
    if pad < 1 or pad > 16 or data[-pad:] != bytes([pad]) * pad:
        raise ValueError("SM4 填充不正确")
    return data[:-pad]


def sm4_encrypt(text: str, key: bytes = SM4_KEY) -> str:
    iv = os.urandom(16)
    encryptor = Cipher(algorithms.SM4(key), modes.CBC(iv)).encryptor()
    ct = encryptor.update(_pkcs7(text.encode("utf-8"))) + encryptor.finalize()
    return "sm4:" + _b64(iv + ct)


def sm4_decrypt(stored: str, key: bytes = SM4_KEY) -> str:
    raw = _unb64(stored.removeprefix("sm4:"))
    iv, ct = raw[:16], raw[16:]
    decryptor = Cipher(algorithms.SM4(key), modes.CBC(iv)).decryptor()
    plain = decryptor.update(ct) + decryptor.finalize()
    return _unpad(plain).decode("utf-8")


def sm4_encrypt_bytes(key: bytes, payload: bytes) -> bytes:
    iv = os.urandom(16)
    encryptor = Cipher(algorithms.SM4(key), modes.CBC(iv)).encryptor()
    ct = encryptor.update(_pkcs7(payload)) + encryptor.finalize()
    mac = hashlib.new("sm3", iv + ct).digest()
    return iv + ct + mac


def sm4_decrypt_bytes(key: bytes, packet: bytes) -> bytes:
    if len(packet) < 16 + 16 + 32:
        raise ValueError("报文过短")
    iv, mac = packet[:16], packet[-32:]
    ct = packet[16:-32]
    expect = hashlib.new("sm3", iv + ct).digest()
    if expect != mac:
        raise ValueError("SM3 校验失败")
    decryptor = Cipher(algorithms.SM4(key), modes.CBC(iv)).decryptor()
    plain = decryptor.update(ct) + decryptor.finalize()
    return _unpad(plain)
