# api.py (patched)
import sys
import asyncio
import os
import json
import shlex
import uuid
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# On Windows, ensure Proactor event loop (subprocess support)
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pymongo import MongoClient
import csv
import io

app = FastAPI(title="Scraper Runner API")

# Allow local dev origins (frontend dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Settings & Paths ---
BASE_DIR = Path(__file__).resolve().parent
SCRAPERS_DIR = BASE_DIR / "Data_Collection" / "Scrapers" / "MD_computers"
ASYNC_SCRAPER = SCRAPERS_DIR / "Async_Scraper.py"
BULK_DATA = SCRAPERS_DIR / "Bulk_data.py"
DATA_DIR = SCRAPERS_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
JOBS_META_DIR = BASE_DIR / "jobs_meta"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(JOBS_META_DIR, exist_ok=True)

MAX_IN_MEMORY_LINES = 500
# concurrency limit for safety (env override)
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))
_JOB_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

# simple token auth (optional; set API_KEY in env to enable)
API_KEY = os.getenv("API_KEY")  # If None, auth is disabled in dev

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "PC_Parts")
try:
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[DB_NAME]
except Exception as e:
    print(f"Warning: Could not connect to MongoDB: {e}")
    mongo_client = None
    mongo_db = None

# Jobs store (in-memory index). Metadata + logs are persisted.
JOBS: Dict[str, Dict[str, Any]] = {}

# --- Pydantic models ---
class StartJobRequest(BaseModel):
    script: str  # "async" or "bulk"
    file: Optional[str] = None
    all: Optional[bool] = False
    categories: Optional[str] = None
    limit: Optional[int] = None
    dry: Optional[bool] = False
    page_limit: Optional[int] = None


# --- Helpers for persistence / util ---
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_meta_path(job_id: str) -> Path:
    return JOBS_META_DIR / f"{job_id}.json"


def _persist_job_meta(job_id: str, meta: Dict[str, Any]):
    try:
        p = _job_meta_path(job_id)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _append_line_to_log(path: Path, line: str):
    try:
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _load_meta(job_id: str) -> Dict[str, Any]:
    try:
        with open(_job_meta_path(job_id), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _require_api_key(x_api_key: Optional[str] = Header(None)):
    """Raise 401 if API_KEY is set and header doesn't match."""
    if API_KEY is None:
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _sanitize_filename(name: str) -> str:
    # prevent path traversal; keep the basename only
    return Path(name).name


# --- Endpoints ---
@app.get("/files")
async def list_data_files():
    files = []
    if DATA_DIR.exists():
        for f in sorted(DATA_DIR.glob("*.json")):
            files.append(f.name)
    return {"data_dir": str(DATA_DIR), "files": files}


@app.post("/jobs/start")
async def start_job(req: StartJobRequest, x_api_key: Optional[str] = Header(None)):
    _require_api_key(x_api_key)

    # concurrency guard
    if _JOB_SEMAPHORE.locked() and _JOB_SEMAPHORE._value <= 0:
        # If semaphore is saturated, signal to client
        # (we still acquire below to keep consistent)
        pass

    if req.script not in ("async", "bulk"):
        raise HTTPException(status_code=400, detail="script must be 'async' or 'bulk'")

    # select script and build args
    if req.script == "async":
        script_path = ASYNC_SCRAPER
        args = []
        if req.all:
            args.append("--all")
        elif req.file:
            args += ["--file", _sanitize_filename(req.file)]
        if req.limit:
            args += ["--limit", str(req.limit)]
        if req.dry:
            args.append("--dry")
    else:
        script_path = BULK_DATA
        args = []
        if req.categories:
            args += ["--categories", _sanitize_filename(req.categories)]
        elif req.all:
            args.append("--all")
        if req.page_limit:
            args += ["--page-limit", str(req.page_limit)]

    if not script_path.exists():
        raise HTTPException(status_code=500, detail=f"Script not found: {script_path}")

    job_id = str(uuid.uuid4())
    cmd = [sys.executable, str(script_path)] + args

    # prepare log file and persisted metadata
    log_path = LOG_DIR / f"job_{job_id}.log"
    meta = {
        "job_id": job_id,
        "cmd": " ".join(shlex.quote(p) for p in cmd),
        "script": req.script,
        "start_time": None,
        "end_time": None,
        "status": "queued",
        "exit_code": None,
        "log_path": str(log_path),
    }
    _persist_job_meta(job_id, meta)

    # Acquire semaphore (non-blocking attempt; will wait here to start)
    await _JOB_SEMAPHORE.acquire()

    # start subprocess in thread (text, utf-8 safe)
    def _start_proc():
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(script_path.parent),
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

    proc = await asyncio.to_thread(_start_proc)

    JOBS[job_id] = {
        "proc": proc,
        "status": "running",
        "lines": [],
        "ws_clients": set(),
        "task": None,
        "cmd": meta["cmd"],
        "log_path": str(log_path),
    }

    meta["start_time"] = _now_iso()
    meta["status"] = "running"
    _persist_job_meta(job_id, meta)

    # spawn reader task
    JOBS[job_id]["task"] = asyncio.create_task(_poll_proc_stdout(job_id))

    return {"job_id": job_id, "cmd": meta["cmd"], "log_path": str(log_path)}


async def _poll_proc_stdout(job_id: str):
    entry = JOBS.get(job_id)
    if not entry:
        return
    proc = entry["proc"]
    log_path = Path(entry.get("log_path"))

    try:
        while True:
            line = await asyncio.to_thread(proc.stdout.readline)
            if not line:
                break
            text = line.rstrip("\r\n")
            # append to buffer
            entry["lines"].append(text)
            if len(entry["lines"]) > MAX_IN_MEMORY_LINES:
                entry["lines"] = entry["lines"][-MAX_IN_MEMORY_LINES:]
            # persist and broadcast
            await asyncio.to_thread(_append_line_to_log, log_path, text)
            await _broadcast_job_line(job_id, text)

        rc = await asyncio.to_thread(proc.wait)
        entry["status"] = "finished" if rc == 0 else f"failed:{rc}"
        # update meta
        meta = _load_meta(job_id)
        meta["end_time"] = _now_iso()
        meta["status"] = entry["status"]
        meta["exit_code"] = rc
        _persist_job_meta(job_id, meta)
        await _broadcast_job_line(job_id, f"__PROCESS_EXIT__:{entry['status']}")
    except asyncio.CancelledError:
        try:
            proc.terminate()
        except Exception:
            pass
        entry["status"] = "terminated"
        await _broadcast_job_line(job_id, "__PROCESS_EXIT__:terminated")
    except Exception as e:
        entry["status"] = f"error:{e}"
        await _broadcast_job_line(job_id, f"__ERROR__:{e}")
    finally:
        # cleanup
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        for ws in list(entry["ws_clients"]):
            try:
                await ws.close()
            except Exception:
                pass
        entry["ws_clients"].clear()
        # release semaphore so another job may start
        try:
            _JOB_SEMAPHORE.release()
        except Exception:
            pass


async def _broadcast_job_line(job_id: str, line: str):
    entry = JOBS.get(job_id)
    if not entry:
        return
    coros = []
    for ws in list(entry["ws_clients"]):
        coros.append(_safe_ws_send(ws, {"type": "log", "line": line}))
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)


async def _safe_ws_send(ws: WebSocket, payload: dict):
    try:
        await ws.send_json(payload)
    except Exception:
        for job in JOBS.values():
            job["ws_clients"].discard(ws)


@app.get("/jobs")
async def list_jobs():
    out = {}
    for jid, info in JOBS.items():
        out[jid] = {
            "status": info["status"],
            "lines": len(info["lines"]),
            "cmd": info.get("cmd"),
            "log_path": info.get("log_path"),
        }
    return out


@app.get("/jobs/meta")
async def list_job_meta():
    """Return persisted job metadata files (useful for UI history)."""
    metas = []
    for p in sorted(JOBS_META_DIR.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                metas.append(json.load(f))
        except Exception:
            pass
    return {"count": len(metas), "jobs": metas}


@app.get("/jobs/{job_id}")
async def job_status(job_id: str):
    info = JOBS.get(job_id)
    if not info:
        # try loading persisted meta
        meta = _load_meta(job_id)
        if meta:
            return {"status": meta.get("status", "unknown"), "last_lines": [], "cmd": meta.get("cmd"), "log_path": meta.get("log_path")}
        raise HTTPException(status_code=404, detail="job not found")
    return {"status": info["status"], "last_lines": info["lines"][-50:], "cmd": info.get("cmd"), "log_path": info.get("log_path")}


@app.get("/jobs/{job_id}/logs")
async def job_logs(job_id: str, tail: int = Query(500, description="Number of last lines to return")):
    meta = _load_meta(job_id)
    if not meta:
        raise HTTPException(status_code=404, detail="job meta not found")
    log_path = Path(meta.get("log_path"))
    if not log_path.exists():
        return {"log": []}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        return {"log": lines[-tail:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/download")
async def download_log(job_id: str):
    """Return the entire log file (for download)."""
    meta = _load_meta(job_id)
    if not meta:
        raise HTTPException(status_code=404, detail="job meta not found")
    log_path = Path(meta.get("log_path"))
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="log not found")
    return {"path": str(log_path)}  # frontend can then fetch via static file serving or another endpoint


@app.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str, x_api_key: Optional[str] = Header(None)):
    _require_api_key(x_api_key)
    info = JOBS.get(job_id)
    if not info:
        raise HTTPException(status_code=404, detail="job not found")
    proc = info.get("proc")
    if proc and getattr(proc, "returncode", None) is None:
        try:
            proc.terminate()
            info["status"] = "terminating"
            meta = _load_meta(job_id)
            meta["status"] = "terminating"
            _persist_job_meta(job_id, meta)
            return {"stopped": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"stopped": False, "reason": "already exited"}


@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_logs(websocket: WebSocket, job_id: str):
    await websocket.accept()
    info = JOBS.get(job_id)
    if not info:
        await websocket.send_json({"type": "error", "msg": "job not found"})
        await websocket.close()
        return

    # add client
    info["ws_clients"].add(websocket)
    # send last 100 lines snapshot
    try:
        for line in info["lines"][-100:]:
            await websocket.send_json({"type": "log", "line": line})
        # reader task will broadcast new lines
        while True:
            await asyncio.sleep(5)
            if websocket.client_state.name != "CONNECTED":
                break
    except WebSocketDisconnect:
        pass
    finally:
        info["ws_clients"].discard(websocket)


# --- MongoDB Collections Endpoints ---
@app.get("/api/collections", response_model=List[str])
async def list_collections():
    """Return list of collection names in the database."""
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="MongoDB not connected")
    try:
        names = mongo_db.list_collection_names()
        return names
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collections/{collection_name}")
async def get_collection_documents(
    collection_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    q: Optional[str] = Query(None),
):
    """Return paginated documents from a collection with optional simple search."""
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="MongoDB not connected")
    col = mongo_db[collection_name]
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    query = {}
    if q:
        # basic search across name and url fields (case-insensitive)
        query = {"$or": [{"name": {"$regex": q, "$options": "i"}}, {"url": {"$regex": q, "$options": "i"}}]}

    skip = (page - 1) * limit
    try:
        cursor = col.find(query).skip(skip).limit(limit)
        docs = []
        for d in cursor:
            d["_id"] = str(d["_id"])
            docs.append(d)
        total = col.count_documents(query)
        return {"collection": collection_name, "page": page, "limit": limit, "total": total, "docs": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collections/{collection_name}/csv")
async def export_collection_csv(collection_name: str, q: Optional[str] = Query(None)):
    """Return CSV attachment for the collection (top-level fields only)."""
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="MongoDB not connected")
    col = mongo_db[collection_name]
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    query = {}
    if q:
        query = {"$or": [{"name": {"$regex": q, "$options": "i"}}, {"url": {"$regex": q, "$options": "i"}}]}

    cursor = col.find(query)

    output = io.StringIO()
    writer = None
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        if writer is None:
            headers = list(doc.keys())
            writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
        writer.writerow(doc)

    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={collection_name}.csv", "Content-Length": str(len(csv_bytes))},
    )


@app.on_event("shutdown")
async def shutdown_event():
    for jid, info in list(JOBS.items()):
        proc = info.get("proc")
        task = info.get("task")
        if task and not task.done():
            task.cancel()
        if proc and getattr(proc, "returncode", None) is None:
            try:
                proc.terminate()
            except Exception:
                pass
    if mongo_client:
        try:
            mongo_client.close()
        except Exception:
            pass
