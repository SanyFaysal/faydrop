import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp

from app.config import (
    load_config,
    save_config,
    get_ffmpeg_path,
    get_node_path,
    STATIC_DIR,
    DEFAULT_DOWNLOAD_DIR,
    TEMP_DOWNLOAD_DIR
)
from app.downloader import (
    analyze_url,
    download_manager,
    identify_platform
)
from app.history import history_manager

app = FastAPI(title="Faydrop Media Downloader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class AnalyzeRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    type: str = "video"       # "video" or "audio"
    quality: str = "best"     # e.g. "1080p", "720p", "320", "best"
    container: str = "mp4"    # "mp4", "mkv", "mp3", "m4a", "wav", "flac"
    custom_filename: Optional[str] = ""
    download_dir: Optional[str] = ""
    device_id: Optional[str] = "guest_default"

class SettingsRequest(BaseModel):
    download_dir: Optional[str] = None
    default_video_quality: Optional[str] = None
    default_audio_format: Optional[str] = None
    default_audio_bitrate: Optional[str] = None
    embed_thumbnail: Optional[bool] = None
    embed_metadata: Optional[bool] = None
    browser_cookies: Optional[str] = None

class PathActionRequest(BaseModel):
    path: str

# Helper to extract device_id
def resolve_device_id(request: Request, param_id: Optional[str] = None) -> str:
    if param_id and param_id.strip():
        return param_id.strip()
    header_val = request.headers.get("x-device-id") or request.headers.get("X-Device-Id")
    if header_val and header_val.strip():
        return header_val.strip()
    return "guest_default"

# API Endpoints
@app.get("/api/system-status")
def system_status():
    ffmpeg_exe = get_ffmpeg_path()
    node_exe = get_node_path()
    config = load_config()

    return {
        "status": "ready",
        "ytdlp_version": yt_dlp.version.__version__,
        "ffmpeg_available": bool(ffmpeg_exe and os.path.exists(ffmpeg_exe)),
        "ffmpeg_path": ffmpeg_exe,
        "node_available": bool(node_exe),
        "node_path": node_exe,
        "download_dir": config.get("download_dir", str(DEFAULT_DOWNLOAD_DIR)),
        "active_jobs_count": len([j for j in download_manager.jobs.values() if j.status in ["queued", "downloading", "processing"]])
    }

@app.post("/api/analyze")
def analyze_endpoint(req: AnalyzeRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Please enter a valid video or audio link.")

    url = req.url.strip()
    try:
        data = analyze_url(url)
        return {"success": True, "data": data}
    except Exception as e:
        err_msg = str(e)
        if "HTTP Error 404" in err_msg:
            friendly = "Media not found (404). Please verify that the link is publicly accessible."
        elif "Private video" in err_msg:
            friendly = "This video is private or member-restricted."
        elif "Sign in to confirm" in err_msg or "bot" in err_msg.lower():
            friendly = "YouTube temporarily throttled requests for this video. Please wait a minute and retry, or try another video."
        elif "Unsupported URL" in err_msg:
            friendly = "The provided URL is not supported or direct media could not be located."
        else:
            friendly = f"Failed to analyze link: {err_msg}"
        return JSONResponse(status_code=400, content={"success": False, "error": friendly})

@app.post("/api/download")
def download_endpoint(req: DownloadRequest, request: Request):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    dev_id = req.device_id or resolve_device_id(request)

    job = download_manager.create_job(
        url=req.url.strip(),
        download_type=req.type,
        quality=req.quality,
        container=req.container,
        custom_filename=req.custom_filename or "",
        download_dir=req.download_dir or "",
        device_id=dev_id
    )
    download_manager.start_download(job.id)
    return {"success": True, "job_id": job.id, "job": job.to_dict()}

@app.get("/api/progress/{job_id}")
def progress_endpoint(job_id: str):
    job = download_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download job not found")
    return job.to_dict()

@app.get("/api/stream-progress/{job_id}")
async def stream_progress_endpoint(job_id: str):
    """Server-Sent Events endpoint for real-time progress updates."""
    job = download_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        import json
        while True:
            current_job = download_manager.get_job(job_id)
            if not current_job:
                break
            payload = json.dumps(current_job.to_dict())
            yield f"data: {payload}\n\n"
            if current_job.status in ["completed", "error", "cancelled"]:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/cancel/{job_id}")
def cancel_endpoint(job_id: str):
    success = download_manager.cancel_job(job_id)
    return {"success": success}

@app.get("/api/jobs")
def list_jobs_endpoint(request: Request, device_id: Optional[str] = None):
    dev_id = resolve_device_id(request, device_id)
    jobs = [j.to_dict() for j in download_manager.jobs.values() if j.device_id == dev_id]
    return {"jobs": sorted(jobs, key=lambda x: x["created_at"], reverse=True)}

# User-specific history endpoints
@app.get("/api/history")
def get_user_history(request: Request, device_id: Optional[str] = None):
    dev_id = resolve_device_id(request, device_id)
    return {"history": history_manager.get_by_device(dev_id), "device_id": dev_id}

@app.delete("/api/history/{item_id}")
def delete_user_history_item(item_id: str, request: Request, device_id: Optional[str] = None, delete_file: bool = False):
    dev_id = resolve_device_id(request, device_id)
    success = history_manager.delete_user_item(item_id, dev_id, delete_file=delete_file)
    return {"success": success}

@app.post("/api/history/clear")
def clear_user_history(request: Request, device_id: Optional[str] = None):
    dev_id = resolve_device_id(request, device_id)
    success = history_manager.clear_user_history(dev_id)
    return {"success": success}

# Admin Control Endpoints (Hidden route & management)
@app.get("/admin-control")
def serve_admin():
    admin_file = STATIC_DIR / "admin.html"
    if admin_file.exists():
        return FileResponse(admin_file)
    return {"message": "Admin interface not found."}

@app.get("/api/admin/stats")
def get_admin_stats():
    return history_manager.get_admin_stats()

@app.get("/api/admin/history")
def get_admin_history(search: Optional[str] = None, device_id: Optional[str] = None):
    return {"history": history_manager.get_admin_history(search=search, filter_device=device_id)}

@app.post("/api/admin/clean-storage")
def clean_storage():
    return history_manager.clean_temp_storage()

@app.delete("/api/admin/history")
def clear_admin_audit():
    return {"success": history_manager.clear_admin_history()}

@app.post("/api/open-folder")
def open_folder(req: PathActionRequest):
    folder_path = req.path
    if not folder_path or not os.path.exists(folder_path):
        config = load_config()
        folder_path = config.get("download_dir", str(DEFAULT_DOWNLOAD_DIR))

    folder_path = os.path.abspath(folder_path)
    if os.path.isfile(folder_path):
        subprocess.run(["explorer", f"/select,{folder_path}"], shell=True)
        return {"success": True, "opened": folder_path}
    elif os.path.isdir(folder_path):
        subprocess.run(["explorer", folder_path], shell=True)
        return {"success": True, "opened": folder_path}
    else:
        raise HTTPException(status_code=404, detail="Path does not exist on disk")

@app.post("/api/open-file")
def open_file(req: PathActionRequest):
    file_path = req.path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File does not exist on disk")

    try:
        os.startfile(file_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open file: {e}")

@app.get("/api/file/{job_id}")
def get_file(job_id: str):
    """
    Direct device download stream: prompts browser on phone/tablet/desktop
    to save directly into the device's native Downloads folder.
    """
    job = download_manager.get_job(job_id)
    target_path = None
    target_name = None

    if job and job.file_path and os.path.exists(job.file_path):
        target_path = job.file_path
        target_name = job.file_name or Path(target_path).name
    else:
        # Check all admin history records
        admin_item = next((i for i in history_manager.get_all() if i.get("id") == job_id), None)
        if admin_item and admin_item.get("file_name"):
            # Check temp_downloads or default
            p1 = TEMP_DOWNLOAD_DIR / admin_item["file_name"]
            p2 = DEFAULT_DOWNLOAD_DIR / admin_item["file_name"]
            if p1.exists():
                target_path = str(p1)
                target_name = admin_item["file_name"]
            elif p2.exists():
                target_path = str(p2)
                target_name = admin_item["file_name"]

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Downloaded media file not found or already cleaned up.")

    # Return file with attachment header to force native device download dialog
    return FileResponse(
        path=target_path,
        filename=target_name,
        media_type="application/octet-stream",
        content_disposition_type="attachment"
    )

@app.get("/api/settings")
def get_settings():
    return load_config()

@app.post("/api/settings")
def update_settings(req: SettingsRequest):
    current = load_config()
    update_data = req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True)
    for k, v in update_data.items():
        if v is not None:
            current[k] = v
    save_config(current)
    return {"success": True, "settings": current}

# Mount static files
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Faydrop API is operational. Place index.html in static/"}
