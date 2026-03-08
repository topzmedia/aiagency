"""
AI Ad Agency — Web Dashboard
Run with: python -m uvicorn ai_ad_agency.web.app:app --reload --port 8000
Then open: http://localhost:8000
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent  # ai_ad_agency/
CONFIGS_DIR = BASE_DIR / "configs"
OUTPUTS_DIR = BASE_DIR / "outputs"
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

# Support running at a subpath (e.g. topzmedia.com/agency)
ROOT_PATH = os.environ.get("ROOT_PATH", "")

app = FastAPI(title="AI Ad Agency", root_path=ROOT_PATH, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------------------------------------------------------------------------
# In-memory job tracker
# ---------------------------------------------------------------------------

_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _job_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")


# ---------------------------------------------------------------------------
# Background task runner
# ---------------------------------------------------------------------------

def _run_generation(job_id: str, config_name: str, pipeline: str, count: int) -> None:
    config_path = CONFIGS_DIR / config_name
    output_dir = OUTPUTS_DIR / job_id

    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["log"] = []

    def log(msg: str) -> None:
        with _jobs_lock:
            _jobs[job_id]["log"].append(msg)

    log(f"Starting {pipeline} generation — count={count}")
    log(f"Config: {config_name}")

    try:
        sys.path.insert(0, str(BASE_DIR.parent))
        from ai_ad_agency.utils.config import load_config
        from ai_ad_agency.models.schemas import OfferConfig

        app_config = load_config(str(BASE_DIR / "configs" / "app_config.json"))
        with open(config_path) as f:
            offer_data = json.load(f)
        offer = OfferConfig(**offer_data)
        output_dir.mkdir(parents=True, exist_ok=True)

        if pipeline in ("hooks", "all"):
            log("Generating hooks...")
            from ai_ad_agency.providers.llm_provider import build_llm_provider
            from ai_ad_agency.agents.hook_agent import HookAgent
            llm = build_llm_provider(app_config.providers.llm)
            agent = HookAgent(app_config, llm)
            hooks = agent.generate_hooks(offer, count=min(count, 30))
            agent.save_hooks(hooks, str(output_dir / "hooks"))
            log(f"Generated {len(hooks)} hooks")

        if pipeline in ("scripts", "all"):
            log("Generating scripts...")
            from ai_ad_agency.providers.llm_provider import build_llm_provider
            from ai_ad_agency.agents.script_agent import ScriptAgent
            llm = build_llm_provider(app_config.providers.llm)
            agent = ScriptAgent(app_config, llm)
            scripts = agent.generate_batch(offer, count=min(count, 20))
            agent.save_scripts(scripts, str(output_dir / "scripts"))
            log(f"Generated {len(scripts)} scripts")

        if pipeline in ("images", "all"):
            log("Generating images...")
            from ai_ad_agency.providers.image_provider import build_image_provider
            from ai_ad_agency.agents.image_agent import ImageAgent
            img_provider = build_image_provider(app_config.providers.image)
            agent = ImageAgent(app_config, img_provider)
            images = agent.generate_batch(offer, count=min(count, 10), output_dir=str(output_dir / "images"))
            log(f"Generated {len(images)} images")

        with _jobs_lock:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["output_dir"] = str(output_dir)
        log("Done!")

    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id]["status"] = "error"
        log(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    configs = [f.name for f in CONFIGS_DIR.glob("*.json") if f.name != "app_config.json"]
    jobs = []
    with _jobs_lock:
        for jid, jdata in sorted(_jobs.items(), reverse=True):
            jobs.append({"id": jid, **jdata})
    return templates.TemplateResponse("index.html", {
        "request": request,
        "configs": configs,
        "jobs": jobs,
    })


@app.post("/generate")
async def generate(
    background_tasks: BackgroundTasks,
    config: str = Form(...),
    pipeline: str = Form(...),
    count: int = Form(10),
):
    job_id = _job_id()
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "config": config,
            "pipeline": pipeline,
            "count": count,
            "log": [],
            "output_dir": None,
            "created_at": datetime.utcnow().isoformat(),
        }
    background_tasks.add_task(_run_generation, job_id, config, pipeline, count)
    return JSONResponse({"job_id": job_id})


@app.get("/job/{job_id}")
async def job_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return JSONResponse(job)


@app.get("/outputs/{job_id}/files")
async def list_outputs(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job or not job.get("output_dir"):
        return JSONResponse({"files": []})

    out_dir = Path(job["output_dir"])
    files = []
    for f in sorted(out_dir.rglob("*")):
        if f.is_file() and not f.name.endswith(".pyc"):
            rel = f.relative_to(OUTPUTS_DIR)
            files.append({
                "name": f.name,
                "path": str(rel),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "ext": f.suffix.lower(),
            })
    return JSONResponse({"files": files})


@app.get("/download/{path:path}")
async def download(path: str):
    file_path = OUTPUTS_DIR / path
    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(str(file_path), filename=file_path.name)
