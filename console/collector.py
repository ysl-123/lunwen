"""感知层。只读本次上传。不打开演示证据目录，不连接演示网站。"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from console.checklist_text import set_materials_dir
from console.fieldclass import classify_storage, storage_algorithm

ROOT = Path(__file__).resolve().parents[1]
UPLOADS = ROOT / "console" / "uploads"
FORBIDDEN = (
    ROOT / "lab" / "evidence",
    ROOT / "samples" / "other-system",
)
REQUIRED_FILES = (
    "profile.json",
    "rows.json",
    "login_summary.json",
    "cert_summary.json",
    "config_export.json",
)
ALLOWED_HOST = "127.0.0.1"
ALLOWED = {
    "http://127.0.0.1:8000": "丙",
    "https://127.0.0.1:8443": "乙",
    "gm://127.0.0.1:9443": "甲",
}
ALLOWED_TOOLS = (
    "current_profile",
    "channel_facts",
    "field_storage",
    "login_observation",
)

_submission: Path | None = None


class AddressRejected(PermissionError):
    pass


def check_target(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.hostname != ALLOWED_HOST:
        raise AddressRejected("地址不在白名单，只允许 127.0.0.1")
    port = parsed.port
    canonical = f"{parsed.scheme}://{ALLOWED_HOST}:{port}"
    if canonical not in ALLOWED:
        raise AddressRejected("只允许 127.0.0.1:8000、8443、9443 这三个入口")
    return canonical


def _forbidden(path: Path) -> bool:
    resolved = path.resolve()
    for banned in FORBIDDEN:
        base = banned.resolve()
        if resolved == base or resolved.is_relative_to(base) or base.is_relative_to(resolved):
            return True
    return False


def set_submission(path: Path) -> Path:
    """计划和报告只读 console/uploads 下的一次提交。"""
    global _submission
    resolved = path.resolve()
    root = UPLOADS.resolve()
    if _forbidden(resolved) or not resolved.is_relative_to(root) or resolved == root:
        raise PermissionError("自测台只读本次上传，不能打开演示证据目录")
    _submission = resolved
    set_materials_dir(resolved / "materials")
    return resolved


def clear_submission() -> None:
    global _submission
    _submission = None
    set_materials_dir(None)


def submission_dir() -> Path:
    if _submission is None:
        raise FileNotFoundError("还没有上传材料")
    if _forbidden(_submission):
        raise PermissionError("自测台只读本次上传，不能打开演示证据目录")
    return _submission


def _read_json(name: str) -> dict:
    path = submission_dir() / name
    if not path.is_file():
        raise FileNotFoundError(f"缺少证据文件 {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def current_profile() -> dict:
    data = _read_json("profile.json")
    return {
        "id": data["fact_id"],
        "tool": "current_profile",
        "data": {"grade": data["grade"], "entry": data["entry"]},
    }


def channel_facts() -> dict:
    data = _read_json("profile.json")
    cert = _read_json("cert_summary.json")
    return {
        "id": data["channel_fact_id"],
        "tool": "channel_facts",
        "data": {
            "protocol": data["protocol"],
            "suite": data["suite"],
            "cert_signature_algorithm": cert.get("signature_algorithm"),
            "note": data.get("note") or cert.get("note") or "",
        },
    }


def field_storage(field_name: str) -> dict:
    if field_name not in ("口令", "手机号"):
        raise ValueError("字段只允许 口令 或 手机号")
    rows = _read_json("rows.json")
    item = rows.get("fields", {}).get(field_name)
    if not item:
        return {
            "id": "F-004" if field_name == "口令" else "F-005",
            "tool": "field_storage",
            "data": {"field": field_name, "storage": "unknown"},
        }
    value = str(item.get("value", ""))
    return {
        "id": item["fact_id"],
        "tool": "field_storage",
        "data": {
            "field": field_name,
            "storage": classify_storage(value),
            "algorithm": storage_algorithm(value),
        },
    }


def login_observation() -> dict:
    data = _read_json("login_summary.json")
    return {
        "id": data["fact_id"],
        "tool": "login_observation",
        "data": {
            "observed": data["observed"],
            "password_in_clear": data["password_in_clear"],
            "protocol": data["protocol"],
            "suite": data["suite"],
        },
    }


def config_facts() -> list[dict]:
    """配置导出仍通过 current_profile 这一采集项读出，不新增工具。"""
    data = _read_json("config_export.json")
    facts = []
    for item in data.get("facts", []):
        payload = dict(item)
        fact_id = payload.pop("id")
        facts.append({"id": fact_id, "tool": "current_profile", "data": payload})
    return facts


def checklist_facts() -> list[dict]:
    path = submission_dir() / "checklist.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    facts = []
    for item in data.get("items", []):
        facts.append(
            {
                "id": item["id"],
                "tool": "current_profile",
                "data": {"clause_id": item["clause_id"], "filename": item.get("filename") or ""},
            }
        )
    return facts


def collect_for_units() -> list[dict]:
    """只调用第 6 节的四个函数。"""
    facts = [
        current_profile(),
        channel_facts(),
        login_observation(),
        field_storage("口令"),
        field_storage("手机号"),
        *config_facts(),
        *checklist_facts(),
    ]
    names = {item["tool"] for item in facts}
    if not names <= set(ALLOWED_TOOLS):
        raise RuntimeError("出现了允许名单之外的采集函数")
    return facts
