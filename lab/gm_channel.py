"""甲档实验信道。只接受 127.0.0.1:9443。

会话密钥用 SM2 加密，报文用 SM4，校验用 SM3。
本机 OpenSSL 没有 GMTLS 套件，所以这不是铜锁的完整握手。
"""

from __future__ import annotations

import json
import os
import socket
import struct

from lab.crypto import sm4_decrypt_bytes, sm4_encrypt_bytes
from lab.openssl_cli import describe_cert, ensure_sm2_cert, sm2_decrypt, sm2_encrypt

HOST = "127.0.0.1"
PORT = 9443
SUITE = "ECC_SM4_CBC_SM3"
NOTE = "实验封装：SM2 保护会话密钥，SM4 保护报文，SM3 做校验。本机 OpenSSL 没有 GMTLS 套件，这不是铜锁完整握手。"


class ChannelError(RuntimeError):
    pass


def _recv_exact(conn: socket.socket, size: int) -> bytes:
    chunks = []
    remain = size
    while remain:
        part = conn.recv(remain)
        if not part:
            raise ChannelError("连接中断")
        chunks.append(part)
        remain -= len(part)
    return b"".join(chunks)


def _send_packet(conn: socket.socket, packet: bytes) -> None:
    if len(packet) > 65536:
        raise ChannelError("报文过长")
    conn.sendall(struct.pack(">I", len(packet)) + packet)


def _recv_packet(conn: socket.socket) -> bytes:
    size = struct.unpack(">I", _recv_exact(conn, 4))[0]
    if size < 1 or size > 65536:
        raise ChannelError("报文长度不允许")
    return _recv_exact(conn, size)


def _client_key(conn: socket.socket) -> tuple[bytes, str]:
    pem = _recv_packet(conn)
    text = describe_cert(pem)
    if "SM2-with-SM3" not in text:
        raise ChannelError("对端证书不是 SM2-with-SM3")
    key = os.urandom(16)
    _send_packet(conn, sm2_encrypt(pem, key))
    return key, "SM2-with-SM3"


def transact(payload: dict) -> dict:
    sock = socket.create_connection((HOST, PORT), timeout=5)
    sock.settimeout(5)
    try:
        peer = sock.getpeername()
        if peer[0] != HOST or peer[1] != PORT:
            raise ChannelError("甲档只允许 127.0.0.1:9443")
        key, _cert = _client_key(sock)
        _send_packet(sock, sm4_encrypt_bytes(key, json.dumps(payload).encode("utf-8")))
        body = sm4_decrypt_bytes(key, _recv_packet(sock))
        return json.loads(body.decode("utf-8"))
    finally:
        sock.close()


def observe_channel() -> dict:
    sock = socket.create_connection((HOST, PORT), timeout=5)
    sock.settimeout(5)
    try:
        if sock.getpeername()[0] != HOST:
            raise ChannelError("甲档只允许 127.0.0.1")
        key, cert_alg = _client_key(sock)
        _send_packet(sock, sm4_encrypt_bytes(key, json.dumps({"op": "health"}).encode("utf-8")))
        body = json.loads(sm4_decrypt_bytes(key, _recv_packet(sock)).decode("utf-8"))
        if body.get("grade") != "甲" or body.get("host") != HOST:
            raise ChannelError("健康检查不是本机甲档")
        return {
            "protocol": "国密TLS",
            "suite": SUITE,
            "cert_signature_algorithm": cert_alg,
            "grade": "甲",
            "note": NOTE,
        }
    finally:
        sock.close()


def serve_forever() -> None:
    from lab.store import authenticate, export_evidence, mark_login_observed, user_profile

    _crt, _key = ensure_sm2_cert()
    pem = _crt.read_bytes()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(8)
    while True:
        conn, addr = server.accept()
        if addr[0] != HOST:
            conn.close()
            continue
        try:
            _handle(conn, pem, authenticate, export_evidence, mark_login_observed, user_profile)
        except Exception:
            pass
        finally:
            conn.close()


def _handle(conn, pem, authenticate, export_evidence, mark_login_observed, user_profile) -> None:
    _send_packet(conn, pem)
    key = sm2_decrypt(_recv_packet(conn))
    if len(key) != 16:
        raise ChannelError("会话密钥长度不正确")
    request = json.loads(sm4_decrypt_bytes(key, _recv_packet(conn)).decode("utf-8"))
    op = request.get("op")
    if op == "health":
        response = {"ok": True, "grade": "甲", "scheme": "gm", "host": HOST}
    elif op == "login":
        username = str(request.get("username", "")).strip()
        password = str(request.get("password", ""))
        if not authenticate(username, password):
            response = {"ok": False, "error": "账号或口令不正确"}
        else:
            mark_login_observed()
            export_evidence()
            from lab.pack import save_zip

            save_zip()
            profile = user_profile(username) or {}
            response = {"ok": True, "phone": profile.get("phone", "")}
    else:
        response = {"ok": False, "error": "未知操作"}
    _send_packet(conn, sm4_encrypt_bytes(key, json.dumps(response, ensure_ascii=False).encode("utf-8")))
