import sys
import asyncio

# On Windows, ensure we use the ProactorEventLoop which supports subprocesses
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        # If running on an older Python where this isn't available, ignore.
        pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
import os
import shlex
import sys
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

app = FastAPI(title="Scraper Runner API")

# Allow local dev origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adjust these paths if your repo layout is different
BASE_DIR = Path(__file__).resolve().parent
SCRAPERS_DIR = BASE_DIR / "Data_Collection" / "Scrapers" / "MD_computers"
ASYNC_SCRAPER = SCRAPERS_DIR / "Async_Scraper.py"
BULK_DATA = SCRAPERS_DIR / "Bulk_data.py"
DATA_DIR = SCRAPERS_DIR / "data"

# Jobs store
JOBS: Dict[str, Dict[str, Any]] = {}
# job structure: {
#   "proc": Process handle (subprocess.Popen),
#   "status": "running"|"finished"|"failed"|"terminating",
#   "lines": [..],
#   "ws_clients": set(WebSocket objs),
#   "task": asyncio.Task (reader)
# }

# simple Pydantic models for request bodies
class StartJobRequest(BaseModel):
    script: str  # "async" or "bulk"
    file: Optional[str] = None
    all: Optional[bool] = False
    categories: Optional[str] = None  # comma separated for bulk
    limit: Optional[int] = None
    dry: Optional[bool] = False
    page_limit: Optional[int] = None


@app.get("/files")
async def list_data_files():
    """List available JSON snapshot files in the scraper's data directory."""
    files = []
    if DATA_DIR.exists():
        for f in sorted(DATA_DIR.glob("*.json")):
            files.append(f.name)
    return {"data_dir": str(DATA_DIR), "files": files}


@app.post("/jobs/start")
async def start_job(req: StartJobRequest):
    """Start a scraper process as a subprocess and stream its stdout/stderr."""
    # select script
    if req.script not in ("async", "bulk"):
        raise HTTPException(status_code=400, detail="script must be 'async' or 'bulk'")

    if req.script == "async":
        script_path = ASYNC_SCRAPER
        # Async_Scraper supports --file, --all, --limit, --dry
        args = []
        if req.all:
            args.append("--all")
        elif req.file:
            args += ["--file", req.file]
        if req.limit:
            args += ["--limit", str(req.limit)]
        if req.dry:
            args.append("--dry")
    else:
        script_path = BULK_DATA
        # Bulk_data supports --categories, --all, --skip-existing/no-skip, --page-limit
        args = []
        if req.categories:
            args += ["--categories", req.categories]
        elif req.all:
            args.append("--all")
        # skip_existing default is True, if user wants to always run they can pass --no-skip via a flag; expose page_limit
        if req.page_limit:
            args += ["--page-limit", str(req.page_limit)]

    if not script_path.exists():
        raise HTTPException(status_code=500, detail=f"Script not found: {script_path}")

    job_id = str(uuid.uuid4())

    # build command using current python executable so venv is respected
    cmd = [sys.executable, str(script_path)] + args

    # Start subprocess using blocking Popen invoked in a thread (works on any event loop)
    def _start_proc():
        # Ensure the child process uses UTF-8 for stdout/stderr so emoji and other
        # unicode characters don't raise encoding/decoding errors when writing to pipes.
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
    }

    # spawn reader task that polls the Popen stdout using threads
    JOBS[job_id]["task"] = asyncio.create_task(_poll_proc_stdout(job_id))

    return {"job_id": job_id, "cmd": " ".join(shlex.quote(p) for p in cmd)}


async def _poll_proc_stdout(job_id: str):
    """Polls a subprocess.Popen stdout in a thread-safe way and broadcasts lines."""
    entry = JOBS.get(job_id)
    if not entry:
        return
    proc = entry["proc"]
    try:
        while True:
            # read a line in a thread so we don't block the event loop
            line = await asyncio.to_thread(proc.stdout.readline)
            if not line:
                break
            text = line.rstrip("

")
            entry["lines"].append(text)
            if len(entry["lines"]) > 500:
                entry["lines"] = entry["lines"][-500:]
            await _broadcast_job_line(job_id, text)

        # wait for process to exit
        rc = await asyncio.to_thread(proc.wait)
        entry["status"] = "finished" if rc == 0 else f"failed:{rc}"
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
        # close any remaining stdout
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        # close websockets
        for ws in list(entry["ws_clients"]):
            try:
                await ws.close()
            except Exception:
                pass
        entry["ws_clients"].clear()


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
        # if sending fails, remove ws from clients
        for job in JOBS.values():
            job["ws_clients"].discard(ws)


@app.get("/jobs")
async def list_jobs():
    out = {}
    for jid, info in JOBS.items():
        out[jid] = {"status": info["status"], "lines": len(info["lines"]) }
    return out


@app.get("/jobs/{job_id}")
async def job_status(job_id: str):
    info = JOBS.get(job_id)
    if not info:
        raise HTTPException(status_code=404, detail="job not found")
    return {"status": info["status"], "last_lines": info["lines"][-50:]}


@app.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    info = JOBS.get(job_id)
    if not info:
        raise HTTPException(status_code=404, detail="job not found")
    proc = info.get("proc")
    if proc and getattr(proc, "returncode", None) is None:
        try:
            proc.terminate()
            info["status"] = "terminating"
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
        # keep connection open; reader task will broadcast new lines
        while True:
            # keepalive ping from client expected; if client disconnects, exit
            await asyncio.sleep(5)
            if websocket.client_state.name != "CONNECTED":
                break
    except WebSocketDisconnect:
        pass
    finally:
        info["ws_clients"].discard(websocket)


# Optional: shutdown handler to gracefully terminate running jobs when API stops
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
