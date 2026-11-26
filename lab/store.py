"""演示库。档位决定口令和手机号在 SQLite 里的形态。"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from lab.crypto import aes_gcm_decrypt, aes_gcm_encrypt, sha256_text, sm3_text, sm4_decrypt, sm4_encrypt

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "lab" / "data"
DB_PATH = DATA_DIR / "app.db"
EVIDENCE_DIR = ROOT / "lab" / "evidence"
LOGIN_RECORD_PATH = DATA_DIR / "login_record.json"

DEMO_USER = "test"
DEMO_PASSWORD = "123456"
DEMO_PHONE = "13800000000"

SCHEMA_SQL = """CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  phone TEXT NOT NULL
);
"""

GRADE_PATH = DATA_DIR / "grade.json"
ENTRIES = {
    "丙": "http://127.0.0.1:8000",
    "乙": "https://127.0.0.1:8443",
    "甲": "gm://127.0.0.1:9443",
}
PROTOCOLS = {"丙": "HTTP", "乙": "TLS", "甲": "国密TLS"}


def get_grade() -> str:
    if not GRADE_PATH.exists():
        return "丙"
    grade = json.loads(GRADE_PATH.read_text(encoding="utf-8")).get("grade", "丙")
    if grade not in ENTRIES:
        raise ValueError("档位只允许甲、乙、丙")
    return grade


def set_grade(grade: str) -> None:
    if grade not in ENTRIES:
        raise ValueError("档位只允许甲、乙、丙")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GRADE_PATH.write_text(json.dumps({"grade": grade}, ensure_ascii=False) + "\n", encoding="utf-8")


def entry_for(grade: str | None = None) -> str:
    return ENTRIES[grade or get_grade()]


def stored_password(password: str, grade: str | None = None) -> str:
    grade = grade or get_grade()
    if grade == "乙":
        return sha256_text(password)
    if grade == "甲":
        return sm3_text(password)
    return password


def stored_phone(phone: str, grade: str | None = None) -> str:
    grade = grade or get_grade()
    if grade == "乙":
        return aes_gcm_encrypt(phone)
    if grade == "甲":
        return sm4_encrypt(phone)
    return phone


def reveal_phone(stored: str, grade: str | None = None) -> str:
    grade = grade or get_grade()
    if grade == "乙":
        return aes_gcm_decrypt(stored)
    if grade == "甲":
        return sm4_decrypt(stored)
    return stored


def connect(readonly: bool = False) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if readonly:
        uri = f"file:{DB_PATH.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection(readonly: bool = False):
    conn = connect(readonly=readonly)
    try:
        yield conn
        if not readonly:
            conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connection(readonly=False) as conn:
        conn.execute(SCHEMA_SQL.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1))
        grade = get_grade()
        conn.execute(
            """
            INSERT INTO users (username, password, phone)
            VALUES (?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
              password = excluded.password,
              phone = excluded.phone
            """,
            (DEMO_USER, stored_password(DEMO_PASSWORD, grade), stored_phone(DEMO_PHONE, grade)),
        )
    if LOGIN_RECORD_PATH.exists():
        LOGIN_RECORD_PATH.unlink()


def authenticate(username: str, password: str) -> bool:
    with connection(readonly=True) as conn:
        row = conn.execute(
            "SELECT password FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if row is None:
        return False
    return row["password"] == stored_password(password)


def user_profile(username: str) -> dict | None:
    with connection(readonly=True) as conn:
        row = conn.execute(
            "SELECT username, phone FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if row is None:
        return None
    return {"username": row["username"], "phone": reveal_phone(row["phone"])}


def mark_login_observed() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    protocol = PROTOCOLS[get_grade()]
    LOGIN_RECORD_PATH.write_text(
        json.dumps(
            {
                "observed": True,
                "password_in_clear": protocol == "HTTP",
                "username": DEMO_USER,
                "protocol": protocol,
                "suite": "无" if protocol == "HTTP" else "待探测",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def read_login_record() -> dict:
    if not LOGIN_RECORD_PATH.exists():
        return {
            "observed": False,
            "password_in_clear": False,
            "username": None,
            "protocol": "HTTP",
            "suite": "无",
        }
    return json.loads(LOGIN_RECORD_PATH.read_text(encoding="utf-8"))


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


def read_user_rows() -> list[dict]:
    with connection(readonly=True) as conn:
        rows = conn.execute(
            "SELECT username, password, phone FROM users ORDER BY id"
        ).fetchall()
    return [
        {
            "username": row["username"],
            "password": row["password"],
            "phone": row["phone"],
        }
        for row in rows
    ]


def export_evidence() -> None:
    """把只读抽样写成 evidence。不读取答案本。"""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_user_rows()
    login = read_login_record()
    grade = get_grade()
    protocol = PROTOCOLS[grade]
    (EVIDENCE_DIR / "schema.sql").write_text(SCHEMA_SQL, encoding="utf-8")
    (EVIDENCE_DIR / "profile.json").write_text(
        json.dumps(
            {
                "fact_id": "F-001",
                "channel_fact_id": "F-002",
                "grade": grade,
                "protocol": protocol,
                "suite": "无" if protocol == "HTTP" else "待探测",
                "cert_signature_algorithm": None,
                "entry": entry_for(grade),
                "note": "",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    field_facts = {}
    if rows:
        sample = rows[0]
        field_facts = {
            "口令": {
                "fact_id": "F-004",
                "column": "password",
                "value": sample["password"],
                "storage": classify_storage(sample["password"]),
                "algorithm": storage_algorithm(sample["password"]),
            },
            "手机号": {
                "fact_id": "F-005",
                "column": "phone",
                "value": sample["phone"],
                "storage": classify_storage(sample["phone"]),
                "algorithm": storage_algorithm(sample["phone"]),
            },
        }
    (EVIDENCE_DIR / "rows.json").write_text(
        json.dumps(
            {"table": "users", "rows": rows, "fields": field_facts},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "cert_summary.json").write_text(
        json.dumps(
            {
                "present": grade != "丙",
                "signature_algorithm": None,
                "dual_cert": False,
                "note": "待探测" if grade != "丙" else "丙档为 HTTP，无证书",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "login_summary.json").write_text(
        json.dumps(
            {
                "fact_id": "F-003",
                "observed": bool(login.get("observed")),
                "password_in_clear": bool(login.get("password_in_clear")),
                "protocol": login.get("protocol") or protocol,
                "suite": login.get("suite") or ("无" if protocol == "HTTP" else "待探测"),
                "username": login.get("username"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_config_export(rows)


def _write_config_export(rows: list[dict]) -> None:
    columns = []
    with connection(readonly=True) as conn:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    integrity = [name for name in columns if name in {"mac", "hmac", "signature", "integrity", "digest"}]
    method = "unknown"
    if rows:
        password = rows[0]["password"]
        if password.startswith("sha256:"):
            method = "sha256"
        elif password.startswith("sm3:"):
            method = "sm3"
        elif classify_storage(password) == "plaintext":
            method = "plaintext"
    payload = {
        "facts": [
            {
                "id": "F-006",
                "topic": "app_login",
                "method": method,
            },
            {
                "id": "F-007",
                "topic": "user_columns",
                "columns": columns,
                "integrity_columns": integrity,
            },
            {
                "id": "F-008",
                "topic": "routes",
                "paths": ["/", "/login", "/profile", "/logout", "/health"],
                "remote_admin": False,
            },
            {"id": "F-009", "topic": "security_label", "present": False},
            {"id": "F-010", "topic": "log_integrity", "present": False},
            {"id": "F-011", "topic": "executable_integrity", "present": False},
            {"id": "F-012", "topic": "non_repudiation", "present": False},
            {"id": "F-013", "topic": "access_control_integrity", "present": False},
            {"id": "F-014", "topic": "device_login", "present": False},
            {"id": "F-015", "topic": "transfer_integrity", "present": False},
        ]
    }
    (EVIDENCE_DIR / "config_export.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def apply_channel_observation(observed: dict) -> None:
    profile_path = EVIDENCE_DIR / "profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["protocol"] = observed["protocol"]
    profile["suite"] = observed["suite"]
    profile["cert_signature_algorithm"] = observed.get("cert_signature_algorithm")
    profile["note"] = observed.get("note") or ""
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE_DIR / "cert_summary.json").write_text(
        json.dumps(
            {
                "present": bool(observed.get("cert_signature_algorithm")),
                "signature_algorithm": observed.get("cert_signature_algorithm"),
                "dual_cert": False,
                "note": observed.get("note") or "",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    login_path = EVIDENCE_DIR / "login_summary.json"
    if login_path.exists():
        login = json.loads(login_path.read_text(encoding="utf-8"))
        login["protocol"] = observed["protocol"]
        login["suite"] = observed["suite"]
        login_path.write_text(json.dumps(login, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
