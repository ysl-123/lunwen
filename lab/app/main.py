"""丙档业务网站。只监听 127.0.0.1:8000，口令明文校验。"""

from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from lab.pack import zip_bytes
from lab.store import (
    authenticate,
    export_evidence,
    get_grade,
    init_db,
    mark_login_observed,
    user_profile,
)

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
SESSIONS: dict[str, str] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    export_evidence()
    yield


app = FastAPI(title="丙档业务网站", lifespan=lifespan)


def current_user(request: Request) -> str | None:
    token = request.cookies.get("sid")
    if not token:
        return None
    return SESSIONS.get(token)


@app.get("/download")
def download_materials():
    payload = zip_bytes()
    filename = "materials.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/health")
def health():
    grade = get_grade()
    scheme = "http" if grade == "丙" else "https"
    return {"ok": True, "grade": grade, "scheme": scheme, "host": "127.0.0.1"}


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    if current_user(request):
        return RedirectResponse("/profile", status_code=303)
    return TEMPLATES.TemplateResponse(
        request,
        "login.html",
        {"error": error, "grade": get_grade()},
    )


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not authenticate(username.strip(), password):
        return TEMPLATES.TemplateResponse(
            request,
            "login.html",
            {"error": "账号或口令不正确", "grade": get_grade()},
            status_code=401,
        )
    mark_login_observed()
    export_evidence()
    token = secrets.token_urlsafe(24)
    SESSIONS[token] = username.strip()
    response = RedirectResponse("/profile", status_code=303)
    response.set_cookie("sid", token, httponly=True, samesite="lax")
    return response


@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    username = current_user(request)
    if not username:
        return RedirectResponse("/", status_code=303)
    row = user_profile(username)
    if row is None:
        return RedirectResponse("/", status_code=303)
    return TEMPLATES.TemplateResponse(
        request,
        "profile.html",
        {"username": row["username"], "phone": row["phone"], "grade": get_grade()},
    )


@app.post("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("sid")
    return response
