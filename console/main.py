"""自测台。只接收上传材料并给出参考结论，不调用演示网站。"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from console.collector import REQUIRED_FILES, UPLOADS, clear_submission, collect_for_units, set_submission
from console.rules import build_plan, build_report, checklist_units, judge

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = Path(__file__).resolve().parent / "data" / "state.json"
TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _bind_submission(state: dict) -> Path | None:
    name = str(state.get("submission") or "").strip()
    if not name or name in {".", ".."} or Path(name).name != name:
        clear_submission()
        return None
    return set_submission(UPLOADS / name)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="自测台", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def material(request: Request):
    state = load_state()
    _bind_submission(state)
    return TEMPLATES.TemplateResponse(
        request,
        "material.html",
        {
            "errors": state.get("errors") or [],
            "message": state.get("message") or "",
            "checklist": checklist_units(),
            "required": REQUIRED_FILES,
            "submission": state.get("submission") or "",
        },
    )


@app.post("/upload")
async def upload(request: Request):
    form = await request.form()
    missing = []
    chosen = {}
    for name in REQUIRED_FILES:
        item = form.get(name)
        filename = str(getattr(item, "filename", "") or "").strip()
        if not filename:
            missing.append(name)
        else:
            chosen[name] = item
    state = load_state()
    if missing:
        state["errors"] = [f"缺少 {name}" for name in missing]
        state["message"] = "上传停住，还缺：" + "、".join(missing)
        state["collected"] = False
        state.pop("submission", None)
        clear_submission()
        save_state(state)
        return RedirectResponse("/", status_code=303)
    submission = UPLOADS / datetime.now().strftime("%Y%m%d%H%M%S%f")
    materials = submission / "materials"
    materials.mkdir(parents=True)
    for name, item in chosen.items():
        (submission / name).write_bytes(await item.read())
    policies = []
    for unit in checklist_units():
        item = form.get(f"policy-{unit['clause_id']}")
        filename = str(getattr(item, "filename", "") or "").strip()
        stored = ""
        if filename:
            base = Path(filename).name
            if base and base not in {".", ".."} and ".." not in Path(base).parts:
                target = materials / f"{unit['clause_id']}-{base}"
                target.write_bytes(await item.read())
                stored = target.name
        policies.append({"id": f"F-CL-{unit['clause_id']}", "clause_id": unit["clause_id"], "filename": stored})
    (submission / "checklist.json").write_text(
        json.dumps({"items": policies}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    set_submission(submission)
    state["submission"] = submission.name
    state["errors"] = []
    state["collected"] = True
    state["message"] = "材料已保存。接下来只读这次提交。"
    state.pop("judgments", None)
    save_state(state)
    return RedirectResponse("/plan", status_code=303)


@app.get("/plan", response_class=HTMLResponse)
def plan(request: Request):
    state = load_state()
    if not state.get("collected") or not state.get("submission"):
        state["message"] = "先上传五份 JSON。缺文件时不会进入计划。"
        save_state(state)
        return RedirectResponse("/", status_code=303)
    state["plan_seen"] = True
    save_state(state)
    return TEMPLATES.TemplateResponse(
        request,
        "plan.html",
        {
            "units": build_plan(),
            "high_risk_count": sum(1 for unit in build_plan() if unit["high_risk"]),
            "message": state.get("message") or "",
        },
    )


@app.post("/start")
def start():
    state = load_state()
    if not state.get("plan_seen") or not state.get("collected"):
        state["message"] = "先在计划页确认后再开始。"
        save_state(state)
        return RedirectResponse("/plan", status_code=303)
    try:
        _bind_submission(state)
        facts = collect_for_units()
    except Exception as exc:  # noqa: BLE001
        state["message"] = f"读取本次提交失败：{exc}"
        save_state(state)
        return RedirectResponse("/", status_code=303)
    judgments = judge(facts)
    report = build_report(judgments, facts)
    state["facts"] = facts
    state["judgments"] = judgments
    state["report"] = report
    state["message"] = "判定完成。"
    save_state(state)
    save_run(report, facts, {"submission": state.get("submission")})
    return RedirectResponse("/result", status_code=303)


@app.get("/result", response_class=HTMLResponse)
def result(request: Request):
    state = load_state()
    if not state.get("judgments"):
        return RedirectResponse("/plan", status_code=303)
    return TEMPLATES.TemplateResponse(
        request,
        "result.html",
        {"judgments": state["judgments"], "facts": state["facts"]},
    )


@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request):
    state = load_state()
    text = state.get("report") or ""
    if not text:
        return RedirectResponse("/result", status_code=303)
    return TEMPLATES.TemplateResponse(request, "report.html", {"report": text})


@app.get("/report.md", response_class=PlainTextResponse)
def report_md():
    state = load_state()
    text = state.get("report") or ""
    if not text:
        return PlainTextResponse("还没有报告", status_code=404)
    return PlainTextResponse(text, media_type="text/markdown; charset=utf-8")


def save_run(report: str, facts: list, archive: dict | None = None) -> Path:
    run_dir = ROOT / "console" / "runs" / datetime.now().strftime("%Y%m%d%H%M%S%f")
    run_dir.mkdir(parents=True)
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (run_dir / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if archive:
        (run_dir / "archive.json").write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run_dir
