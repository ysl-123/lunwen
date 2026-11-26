"""清单文字对照。只从本次上传的制度文件里摘原句，不写结论，不访问网络。"""

from __future__ import annotations

import os
from pathlib import Path

_materials: Path | None = None


def set_materials_dir(path: Path | None) -> None:
    global _materials
    _materials = path


def model_configured() -> bool:
    return bool(os.environ.get("CHECKLIST_MODEL", "").strip())


def resolve_material(filename: str) -> Path | None:
    raw = str(filename or "").strip()
    if not raw or _materials is None:
        return None
    candidate = Path(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    root = _materials.resolve()
    try:
        path = (root / candidate).resolve()
    except OSError:
        return None
    if path == root or not path.is_relative_to(root) or not path.is_file():
        return None
    return path


def read_material(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def matching_quote(file_text: str, excerpt: str) -> str | None:
    """只摘文件里的原句。未配置 CHECKLIST_MODEL 时不访问网络；对不上就返回空。"""
    if model_configured():
        return _verbatim(file_text, excerpt)
    return _verbatim(file_text, excerpt)


def _verbatim(file_text: str, excerpt: str) -> str | None:
    sentence = excerpt.strip()
    if not sentence:
        return None
    index = file_text.find(sentence)
    if index < 0:
        return None
    quote = file_text[index : index + len(sentence)]
    if quote != sentence or quote not in file_text:
        return None
    return quote
