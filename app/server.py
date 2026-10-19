import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
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
    DEFAULT_DOWNLOAD_DIR
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
            friendly = "Media not found (404). Please verify that the link is correct and publicly accessible."
        elif "Private video" in err_msg:
            friendly = "This video is private. If it is your private content, select your browser in Settings to use your cookies."
        elif "Sign in to confirm" in err_msg:
            friendly = "YouTube bot verification triggered. Try selecting your browser in Settings or try again in a few moments."
        elif "Unsupported URL" in err_msg:
            friendly = "The provided URL is not supported or direct media could not be located."
        else:
            friendly = f"Failed to analyze link: {err_msg}"
        return JSONResponse(status_code=400, content={"success": False, "error": friendly})

@app.post("/api/download")
def download_endpoint(req: DownloadRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    job = download_manager.create_job(
        url=req.url.strip(),
        download_type=req.type,
        quality=req.quality,
        container=req.container,
        custom_filename=req.custom_filename or "",
        download_dir=req.download_dir or ""
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
def list_jobs_endpoint():
    jobs = [j.to_dict() for j in download_manager.jobs.values()]
    return {"jobs": sorted(jobs, key=lambda x: x["created_at"], reverse=True)}

@app.get("/api/history")
def get_history():
    return {"history": history_manager.get_all()}

@app.delete("/api/history/{item_id}")
def delete_history_item(item_id: str, delete_file: bool = False):
    success = history_manager.delete_item(item_id, delete_file=delete_file)
    return {"success": success}

@app.post("/api/history/clear")
def clear_history():
    success = history_manager.clear_all()
    return {"success": success}

@app.post("/api/open-folder")
def open_folder(req: PathActionRequest):
    folder_path = req.path
    if not folder_path or not os.path.exists(folder_path):
        config = load_config()
        folder_path = config.get("download_dir", str(DEFAULT_DOWNLOAD_DIR))

    folder_path = os.path.abspath(folder_path)
    if os.path.isfile(folder_path):
        # Open explorer and select the file
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
    job = download_manager.get_job(job_id)
    if not job or not job.file_path or not os.path.exists(job.file_path):
        # Check history
        history_item = next((i for i in history_manager.get_all() if i.get("id") == job_id), None)
        if history_item and history_item.get("file_path") and os.path.exists(history_item["file_path"]):
            filepath = history_item["file_path"]
            filename = history_item.get("file_name", Path(filepath).name)
            return FileResponse(filepath, filename=filename, media_type="application/octet-stream")
        raise HTTPException(status_code=404, detail="Downloaded file not found")

    return FileResponse(job.file_path, filename=job.file_name, media_type="application/octet-stream")

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
    return {"message": "Downloader API is operational. Place index.html in static/"}
