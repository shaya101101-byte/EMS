# routes/admin.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import os
import json
import time
from pathlib import Path

from utils.request_logger import (
    list_history_jsons,
    read_history_json,
    list_uploaded_images,
    get_db_history,
)

ADMIN_TOKEN = "ADMIN_TOKEN"

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parents[1] / "templates"))


def check_token(request: Request):
    """Verify admin token from x-admin-token header or ?token= query parameter."""
    token = request.headers.get("x-admin-token") or request.query_params.get("token")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ===== HTML Pages (serve templates) =====

@router.get("/admin", response_class=HTMLResponse)
def admin_index(request: Request):
    check_token(request)
    return templates.TemplateResponse("admin/index.html", {"request": request})


@router.get("/admin/history", response_class=HTMLResponse)
def admin_history(request: Request):
    check_token(request)
    return templates.TemplateResponse("admin/history.html", {"request": request})


@router.get("/admin/view/{identifier}", response_class=HTMLResponse)
def admin_view(request: Request, identifier: str):
    check_token(request)
    # Try numeric ID first
    try:
        iid = int(identifier)
        db = get_db_history(limit=1000)
        for row in db:
            if row.get("id") == iid:
                return templates.TemplateResponse("admin/view.html", {"request": request, "item": row})
    except Exception:
        pass

    # else treat as filename
    possible = read_history_json(identifier)
    if possible:
        return templates.TemplateResponse("admin/view.html", {"request": request, "item": possible})
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/admin/uploads", response_class=HTMLResponse)
def admin_uploads(request: Request):
    check_token(request)
    return templates.TemplateResponse("admin/uploads.html", {"request": request})


@router.get("/admin/logs", response_class=HTMLResponse)
def admin_logs(request: Request):
    check_token(request)
    return templates.TemplateResponse("admin/logs.html", {"request": request})


@router.get("/admin/stats", response_class=HTMLResponse)
def admin_stats(request: Request):
    check_token(request)
    return templates.TemplateResponse("admin/stats.html", {"request": request})


@router.get("/admin/events", response_class=HTMLResponse)
def admin_events(request: Request):
    check_token(request)
    return templates.TemplateResponse("admin/events.html", {"request": request})


# ===== JSON API Endpoints =====

@router.get("/admin/api/history", response_class=JSONResponse)
def api_history(request: Request):
    check_token(request)
    # Combine DB history and JSON files
    db_hist = get_db_history(limit=200)
    json_files = list_history_jsons()
    json_hist = [read_history_json(p) for p in json_files]
    return JSONResponse({"db": db_hist, "files": json_hist})


@router.get("/admin/api/uploads", response_class=JSONResponse)
def api_uploads(request: Request):
    check_token(request)
    imgs = list_uploaded_images()
    return JSONResponse({"images": imgs})


@router.get("/admin/api/stats", response_class=JSONResponse)
def api_stats(request: Request):
    check_token(request)
    # Aggregate stats from DB and JSON history
    db = get_db_history(limit=1000)
    total = len(db)
    per_class = {}
    for r in db:
        counts = r.get("counts") or {}
        for k, v in counts.items():
            per_class[k] = per_class.get(k, 0) + int(v)
    return JSONResponse({"total_analyses": total, "per_class": per_class})


@router.get("/admin/api/events/stream")
def events_stream(request: Request):
    check_token(request)

    def event_generator():
        seen = set()
        while True:
            # Poll DB history
            rows = get_db_history(limit=50)
            for r in rows:
                rid = r.get("id")
                if rid not in seen:
                    seen.add(rid)
                    data = json.dumps(r, default=str)
                    yield f"data: {data}\n\n"
            # Also poll JSON files
            for p in list_history_jsons():
                rec = read_history_json(p)
                key = rec.get("filename") or rec.get("id") or p
                if key not in seen:
                    seen.add(key)
                    yield f"data: {json.dumps(rec, default=str)}\n\n"
            time.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
