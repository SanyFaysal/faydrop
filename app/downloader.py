import os
import re
import time
import math
import uuid
import threading
import subprocess
import traceback
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import yt_dlp

from app.config import (
    BASE_DIR,
    load_config,
    get_ffmpeg_path,
    get_ffmpeg_dir,
    get_node_path,
    DEFAULT_DOWNLOAD_DIR,
    TEMP_DOWNLOAD_DIR
)
from app.history import history_manager

class DownloadCancelledException(Exception):
    """Raised when user cancels download."""
    pass

def sanitize_filename(name: str) -> str:
    """Sanitizes filename for Windows filesystem and trims length."""
    # Replace illegal characters
    cleaned = re.sub(r'[\\/*?:"<>|\r\n\t]', "", name)
    cleaned = cleaned.strip(". ")
    if not cleaned:
        cleaned = "download"
    # Ensure filename isn't ridiculously long
    if len(cleaned) > 180:
        cleaned = cleaned[:180].strip()
    return cleaned

def format_bytes(bytes_num: Optional[float]) -> str:
    """Formats bytes into human readable string (KB, MB, GB)."""
    if not bytes_num or bytes_num <= 0:
        return "Unknown size"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while bytes_num >= 1024 and i < len(units) - 1:
        bytes_num /= 1024.0
        i += 1
    return f"{bytes_num:.1f} {units[i]}"

def format_seconds(seconds: Optional[float]) -> str:
    """Formats seconds into HH:MM:SS or MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def identify_platform(url: str) -> dict:
    """Detects platform and returns metadata info and brand color/icon."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return {
            "name": "YouTube",
            "key": "youtube",
            "icon": "youtube",
            "color": "#FF0000"
        }
    elif "facebook.com" in url_lower or "fb.watch" in url_lower or "fb.com" in url_lower:
        return {
            "name": "Facebook",
            "key": "facebook",
            "icon": "facebook",
            "color": "#1877F2"
        }
    elif "instagram.com" in url_lower:
        return {
            "name": "Instagram",
            "key": "instagram",
            "icon": "instagram",
            "color": "#E4405F"
        }
    elif "tiktok.com" in url_lower:
        return {
            "name": "TikTok",
            "key": "tiktok",
            "icon": "music-2",
            "color": "#00F2FE"
        }
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return {
            "name": "X (Twitter)",
            "key": "twitter",
            "icon": "twitter",
            "color": "#1DA1F2"
        }
    elif "reddit.com" in url_lower:
        return {
            "name": "Reddit",
            "key": "reddit",
            "icon": "message-square",
            "color": "#FF4500"
        }
    elif "vimeo.com" in url_lower:
        return {
            "name": "Vimeo",
            "key": "vimeo",
            "icon": "video",
            "color": "#1AB7EA"
        }
    elif "soundcloud.com" in url_lower:
        return {
            "name": "SoundCloud",
            "key": "soundcloud",
            "icon": "headphones",
            "color": "#FF5500"
        }
    return {
        "name": "Web Media",
        "key": "generic",
        "icon": "globe",
        "color": "#8B5CF6"
    }

def get_base_ydl_opts(config: dict = None) -> dict:
    """Constructs robust base yt-dlp options with FFmpeg, FFprobe, and JS runtime."""
    if config is None:
        config = load_config()

    ffmpeg_dir = get_ffmpeg_dir() or get_ffmpeg_path()
    node_path = get_node_path()

    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 30,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        },
        "remote_components": ["ejs:github"],
        "extractor_args": {
            "youtube": {
                "player_client": ["visionos", "android", "ios"],
                "formats": ["missing_pot"]
            }
        }
    }

    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir

    if node_path:
        opts["js_runtimes"] = {"node": {"path": node_path}}

    # Cookie support: 1. check for cookies.txt file in project root
    cookies_file = BASE_DIR / "cookies.txt"
    if cookies_file.exists():
        opts["cookiefile"] = str(cookies_file)
    else:
        browser = config.get("browser_cookies", "none")
        if browser and browser != "none":
            opts["cookiesfrombrowser"] = (browser, None, None, None)

    return opts

def analyze_url(url: str) -> dict:
    """
    Extracts comprehensive metadata, thumbnails, and available audio/video formats
    from the target link without downloading.
    """
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty")

    platform = identify_platform(url)
    config = load_config()
    ydl_opts = get_base_ydl_opts(config)

    info = None
    last_error = None

    # Multi-client ladder for YouTube to avoid bot verification
    if platform["key"] == "youtube":
        client_attempts = [
            ["tv_simply"],
            ["visionos", "android", "ios"],
            ["mweb", "android"],
            ["android", "ios"],
            ["android"],
            ["ios"]
        ]
    else:
        client_attempts = [None]

    for clients in client_attempts:
        if clients:
            ydl_opts["extractor_args"]["youtube"]["player_client"] = clients
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    break
        except Exception as e:
            last_error = e
            continue

    if not info:
        if last_error:
            raise last_error
        raise ValueError("Could not extract media info from this URL")

    # If it's a playlist or multiple entries, pick the first or primary
    if "entries" in info and info["entries"]:
        first_entry = next((e for e in info["entries"] if e), None)
        if first_entry:
            info = first_entry

    duration = info.get("duration")
    duration_str = format_seconds(duration)
    title = info.get("title", "Untitled Media")
    uploader = info.get("uploader") or info.get("channel") or info.get("creator") or platform["name"]
    thumbnail = info.get("thumbnail") or (info.get("thumbnails")[-1]["url"] if info.get("thumbnails") else "")
    view_count = info.get("view_count")
    upload_date = info.get("upload_date")
    webpage_url = info.get("webpage_url", url)

    raw_formats = info.get("formats", [])

    # Process and categorize formats
    video_formats = []
    audio_formats = []

    # Map of standard resolutions
    resolutions_seen = set()

    # Sort formats by resolution / tbr descending
    sorted_formats = sorted(
        raw_formats,
        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
        reverse=True
    )

    for f in sorted_formats:
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        height = f.get("height")
        ext = f.get("ext", "mp4")
        tbr = f.get("tbr") or 0
        fps = f.get("fps") or 30

        # Video streams
        if vcodec != "none" and height and height >= 144:
            res_key = f"{height}p"
            if res_key not in resolutions_seen:
                resolutions_seen.add(res_key)

                # Quality label & badges
                badge = ""
                quality_label = f"{height}p"
                if height >= 2160:
                    badge = "4K Ultra HD"
                elif height >= 1440:
                    badge = "2K Quad HD"
                elif height >= 1080:
                    badge = "Full HD"
                elif height >= 720:
                    badge = "HD"
                else:
                    badge = "SD"

                # Estimate size if missing
                filesize = f.get("filesize") or f.get("filesize_approx")
                if not filesize and duration and tbr:
                    filesize = int((tbr * 1024 * duration) / 8)

                video_formats.append({
                    "format_id": f.get("format_id"),
                    "resolution": res_key,
                    "height": height,
                    "fps": int(fps),
                    "badge": badge,
                    "vcodec": vcodec.split(".")[0] if vcodec else "mp4v",
                    "has_audio": acodec != "none",
                    "filesize": filesize,
                    "filesize_str": format_bytes(filesize) if filesize else "Adaptive Size",
                    "ext": "mp4"
                })

    # If no separate streams were found (e.g. single direct mp4), add default best
    if not video_formats:
        video_formats.append({
            "format_id": "best",
            "resolution": "Best Available",
            "height": 1080,
            "fps": 30,
            "badge": "Original",
            "vcodec": "default",
            "has_audio": True,
            "filesize": None,
            "filesize_str": "Best Available",
            "ext": "mp4"
        })

    # Prepare standard Audio options
    audio_presets = [
        {"format_id": "mp3-320", "codec": "mp3", "bitrate": "320", "title": "MP3 • 320 kbps", "badge": "High Fidelity (Best)", "rate": 320},
        {"format_id": "mp3-256", "codec": "mp3", "bitrate": "256", "title": "MP3 • 256 kbps", "badge": "High Quality", "rate": 256},
        {"format_id": "mp3-192", "codec": "mp3", "bitrate": "192", "title": "MP3 • 192 kbps", "badge": "Standard", "rate": 192},
        {"format_id": "mp3-128", "codec": "mp3", "bitrate": "128", "title": "MP3 • 128 kbps", "badge": "Compact", "rate": 128},
        {"format_id": "m4a",     "codec": "m4a", "bitrate": "auto", "title": "M4A • Original AAC", "badge": "Fastest (No re-encode)", "rate": 160},
        {"format_id": "wav",     "codec": "wav", "bitrate": "lossless", "title": "WAV • Uncompressed", "badge": "Studio Lossless", "rate": 1411},
        {"format_id": "flac",    "codec": "flac", "bitrate": "lossless", "title": "FLAC • Lossless", "badge": "Hi-Res Audio", "rate": 800}
    ]

    for preset in audio_presets:
        est_size = None
        if duration:
            est_size = int((preset["rate"] * 1024 * duration) / 8)
        audio_formats.append({
            "format_id": preset["format_id"],
            "codec": preset["codec"],
            "bitrate": preset["bitrate"],
            "title": preset["title"],
            "badge": preset["badge"],
            "filesize": est_size,
            "filesize_str": format_bytes(est_size) if est_size else "Varies by duration",
            "ext": preset["codec"]
        })

    return {
        "url": webpage_url,
        "title": title,
        "uploader": uploader,
        "duration": duration,
        "duration_str": duration_str,
        "thumbnail": thumbnail,
        "view_count": view_count,
        "view_count_str": f"{view_count:,}" if view_count else None,
        "upload_date": upload_date,
        "platform": platform,
        "video_formats": video_formats,
        "audio_formats": audio_formats
    }

class DownloadJob:
    def __init__(self, job_id: str, url: str, download_type: str, quality: str, container: str, custom_filename: str = "", download_dir: str = "", device_id: str = "guest_default"):
        self.id = job_id
        self.url = url
        self.type = download_type  # 'video' or 'audio'
        self.quality = quality     # e.g. '1080p', '720p', 'mp3-320', etc.
        self.container = container # 'mp4', 'mkv', 'mp3', 'm4a', 'wav', 'flac'
        self.custom_filename = custom_filename
        self.download_dir = download_dir or str(TEMP_DOWNLOAD_DIR)
        self.device_id = device_id or "guest_default"

        self.title = "Initializing..."
        self.thumbnail = ""
        self.platform = identify_platform(url)
        self.status = "queued"     # queued, downloading, processing, completed, error, cancelled
        self.progress = 0.0
        self.speed_str = "0 B/s"
        self.eta_str = "--:--"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.downloaded_str = "0 MB"
        self.total_str = "0 MB"
        self.file_path = ""
        self.file_name = ""
        self.error_message = ""
        self.cancelled = False
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "url": self.url,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "type": self.type,
            "quality": self.quality,
            "container": self.container,
            "platform": self.platform,
            "status": self.status,
            "progress": round(self.progress, 1),
            "speed_str": self.speed_str,
            "eta_str": self.eta_str,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "downloaded_str": self.downloaded_str,
            "total_str": self.total_str,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "error_message": self.error_message,
            "created_at": self.created_at
        }

class DownloadManager:
    def __init__(self):
        self.jobs: Dict[str, DownloadJob] = {}
        self.lock = threading.Lock()

    def create_job(self, url: str, download_type: str, quality: str, container: str, custom_filename: str = "", download_dir: str = "", device_id: str = "guest_default") -> DownloadJob:
        job_id = str(uuid.uuid4())[:10]
        job = DownloadJob(
            job_id=job_id,
            url=url,
            download_type=download_type,
            quality=quality,
            container=container,
            custom_filename=custom_filename,
            download_dir=download_dir,
            device_id=device_id
        )
        with self.lock:
            self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        with self.lock:
            return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.status in ["queued", "downloading", "processing"]:
                job.cancelled = True
                job.status = "cancelled"
                job.error_message = "Download was cancelled by user"
                return True
        return False

    def start_download(self, job_id: str):
        job = self.get_job(job_id)
        if not job:
            return
        thread = threading.Thread(target=self._run_download, args=(job,), daemon=True)
        thread.start()

    def _progress_hook(self, job: DownloadJob, d: dict):
        if job.cancelled:
            raise DownloadCancelledException("Download cancelled by user")

        status = d.get("status")
        if status == "downloading":
            job.status = "downloading"
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            speed = d.get("speed", 0)
            eta = d.get("eta")

            job.downloaded_bytes = downloaded
            job.total_bytes = total

            if total and total > 0:
                job.progress = min(99.0, (downloaded / total) * 100.0)
            else:
                job.progress = min(95.0, job.progress + 0.5)

            job.speed_str = f"{format_bytes(speed)}/s" if speed else "Calculating..."
            job.eta_str = format_seconds(eta)
            job.downloaded_str = format_bytes(downloaded)
            job.total_str = format_bytes(total) if total else "Unknown"
            job.updated_at = time.time()

        elif status == "finished":
            job.status = "processing"
            job.progress = 99.0
            job.speed_str = "Processing with FFmpeg..."
            job.eta_str = "Almost done..."
            job.updated_at = time.time()

    def _run_download(self, job: DownloadJob):
        config = load_config()
        download_dir = Path(job.download_dir or config.get("download_dir", str(DEFAULT_DOWNLOAD_DIR)))
        download_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = get_base_ydl_opts(config)
        ydl_opts["progress_hooks"] = [lambda d: self._progress_hook(job, d)]

        # Custom or default template
        safe_title = sanitize_filename(job.custom_filename) if job.custom_filename else "%(title)s"
        outtmpl = str(download_dir / f"{safe_title}.%(ext)s")
        ydl_opts["outtmpl"] = outtmpl

        # Configure video vs audio options
        if job.type == "audio":
            codec = job.container if job.container in ["mp3", "m4a", "wav", "flac"] else "mp3"
            quality_bitrate = "320"
            if "320" in job.quality:
                quality_bitrate = "320"
            elif "256" in job.quality:
                quality_bitrate = "256"
            elif "192" in job.quality:
                quality_bitrate = "192"
            elif "128" in job.quality:
                quality_bitrate = "128"

            ydl_opts["format"] = "bestaudio/best"
            postprocessors = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": codec,
                    "preferredquality": quality_bitrate
                }
            ]
            if config.get("embed_metadata", True):
                postprocessors.append({"key": "FFmpegMetadata"})
            if config.get("embed_thumbnail", True) and codec in ["mp3", "m4a"]:
                ydl_opts["writethumbnail"] = True
                postprocessors.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg"})
                postprocessors.append({"key": "EmbedThumbnail"})

            ydl_opts["postprocessors"] = postprocessors

        else: # Video download
            container = job.container if job.container in ["mp4", "mkv"] else "mp4"
            height = None
            if "p" in job.quality:
                try:
                    height = int(job.quality.replace("p", ""))
                except Exception:
                    pass

            if height:
                # Merge best video matching height with best audio, with graceful fallbacks
                ydl_opts["format"] = f"bestvideo[height<={height}]+bestaudio/bestvideo[height<={height}]+best/best[height<={height}]/best"
            else:
                ydl_opts["format"] = "bestvideo+bestaudio/bestvideo+best/best"

            ydl_opts["merge_output_format"] = container
            postprocessors = []
            if config.get("embed_metadata", True):
                postprocessors.append({"key": "FFmpegMetadata"})
            if config.get("embed_thumbnail", True):
                ydl_opts["writethumbnail"] = True
                postprocessors.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg"})
                postprocessors.append({"key": "EmbedThumbnail"})
            if postprocessors:
                ydl_opts["postprocessors"] = postprocessors

        try:
            job.status = "downloading"
            
            is_youtube = job.platform.get("key") == "youtube" if isinstance(job.platform, dict) else "youtube" in job.url.lower()
            if is_youtube:
                client_ladder = [
                    ["tv_simply"],
                    ["visionos", "android", "ios"],
                    ["mweb", "android"],
                    ["android", "ios"],
                    ["android"]
                ]
            else:
                client_ladder = [None]

            info = None
            last_download_err = None
            successful_ydl = None

            for clients in client_ladder:
                if job.cancelled:
                    job.status = "cancelled"
                    return

                current_opts = dict(ydl_opts)
                if clients:
                    current_opts["extractor_args"] = {
                        "youtube": {
                            "player_client": clients,
                            "formats": ["missing_pot"]
                        }
                    }

                try:
                    with yt_dlp.YoutubeDL(current_opts) as ydl:
                        info = ydl.extract_info(job.url, download=True)
                        if info:
                            successful_ydl = ydl
                            break
                except Exception as dl_err:
                    last_download_err = dl_err
                    err_text = str(dl_err).lower()
                    print(f"[Downloader] Client attempt {clients} encountered: {dl_err}")

                    # If 403 Forbidden or format missing on DASH streams, retry this client with pre-merged 'best'
                    if ("403" in err_text or "format" in err_text) and not job.cancelled:
                        try:
                            dash_fallback = dict(current_opts)
                            dash_fallback["format"] = "best"
                            with yt_dlp.YoutubeDL(dash_fallback) as fb_ydl:
                                info = fb_ydl.extract_info(job.url, download=True)
                                if info:
                                    successful_ydl = fb_ydl
                                    break
                        except Exception as fb403:
                            last_download_err = fb403

                    # If thumbnail postprocessing or ffprobe glitch, retry safely without thumbnail
                    if ("ffprobe" in err_text or "embed" in err_text or "postprocessing" in err_text) and not job.cancelled:
                        try:
                            fallback_opts = dict(current_opts)
                            fallback_opts.pop("writethumbnail", None)
                            fallback_opts["postprocessors"] = [
                                p for p in fallback_opts.get("postprocessors", []) 
                                if p.get("key") not in ["EmbedThumbnail", "FFmpegThumbnailsConvertor"]
                            ]
                            with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                                info = fallback_ydl.extract_info(job.url, download=True)
                                if info:
                                    successful_ydl = fallback_ydl
                                    break
                        except Exception as fb_err:
                            last_download_err = fb_err

                    # Otherwise continue to next client in the ladder

            if not info and last_download_err:
                raise last_download_err

            if info:
                job.title = info.get("title", job.title)
                job.thumbnail = info.get("thumbnail") or job.thumbnail

                # Detect final file
                ydl_instance = successful_ydl or yt_dlp.YoutubeDL(ydl_opts)
                expected_filename = ydl_instance.prepare_filename(info)
                target_ext = job.container
                base_stem = Path(expected_filename).stem
                possible_file = download_dir / f"{base_stem}.{target_ext}"

                if possible_file.exists():
                    job.file_path = str(possible_file)
                    job.file_name = possible_file.name
                elif Path(expected_filename).exists():
                    job.file_path = expected_filename
                    job.file_name = Path(expected_filename).name
                else:
                    # Find most recently modified file in download_dir
                    matched = list(download_dir.glob(f"{base_stem}*"))
                    if matched:
                        newest = max(matched, key=os.path.getmtime)
                        job.file_path = str(newest)
                        job.file_name = newest.name

            # Explicit audio conversion guarantee: Ensure downloaded file is transcoded to target audio format
            if job.type == "audio" and job.file_path and os.path.exists(job.file_path):
                current_path = Path(job.file_path)
                target_ext = (job.container or "mp3").lower().lstrip(".")
                
                # Check if file has the requested audio extension
                if current_path.suffix.lower().lstrip(".") != target_ext:
                    converted_audio_path = download_dir / f"{current_path.stem}.{target_ext}"
                    ffmpeg_exe = get_ffmpeg_path()
                    if ffmpeg_exe:
                        job.status = "processing"
                        job.progress = 99.0
                        job.speed_str = f"Transcoding to {target_ext.upper()}..."
                        
                        cmd = [ffmpeg_exe, "-y", "-i", str(current_path), "-vn"]
                        if target_ext == "mp3":
                            bitrate = "320k"
                            if "256" in job.quality:
                                bitrate = "256k"
                            elif "192" in job.quality:
                                bitrate = "192k"
                            elif "128" in job.quality:
                                bitrate = "128k"
                            cmd.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
                        elif target_ext == "m4a":
                            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
                        elif target_ext == "wav":
                            cmd.extend(["-c:a", "pcm_s16le"])
                        elif target_ext == "flac":
                            cmd.extend(["-c:a", "flac"])
                        else:
                            cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k"])
                            
                        cmd.append(str(converted_audio_path))
                        print(f"[Downloader] Converting video stream to audio ({target_ext}): {' '.join(cmd)}")
                        try:
                            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                            if res.returncode == 0 and converted_audio_path.exists():
                                # Remove original unconverted video stream
                                try:
                                    if current_path.resolve() != converted_audio_path.resolve() and current_path.exists():
                                        current_path.unlink()
                                except Exception as rm_err:
                                    print(f"[Downloader] Cleanup notice: {rm_err}")
                                job.file_path = str(converted_audio_path)
                                job.file_name = converted_audio_path.name
                        except Exception as conv_err:
                            print(f"[Downloader] Audio transcode fallback error: {conv_err}")

            if job.cancelled:
                job.status = "cancelled"
                return

            job.status = "completed"
            job.progress = 100.0
            job.speed_str = "Done"
            job.eta_str = "Finished"

            # Add to history
            file_size_bytes = os.path.getsize(job.file_path) if job.file_path and os.path.exists(job.file_path) else job.total_bytes
            history_manager.add_item({
                "id": job.id,
                "url": job.url,
                "title": job.title,
                "thumbnail": job.thumbnail,
                "platform": job.platform,
                "type": job.type,
                "quality": job.quality,
                "format": job.container,
                "file_path": job.file_path,
                "file_name": job.file_name,
                "file_size": file_size_bytes,
                "file_size_str": format_bytes(file_size_bytes),
                "status": "completed"
            }, device_id=job.device_id)

        except DownloadCancelledException:
            job.status = "cancelled"
            job.error_message = "Download cancelled by user"
        except Exception as e:
            if job.cancelled:
                job.status = "cancelled"
                job.error_message = "Download cancelled by user"
            else:
                job.status = "error"
                clean_err = str(e)
                if "Sign in to confirm" in clean_err or "bot" in clean_err.lower():
                    clean_err = "YouTube temporarily rate-limited requests from this session. Please wait a moment and try again."
                elif "Private video" in clean_err:
                    clean_err = "This media is private or requires authorization."
                elif "Video unavailable" in clean_err:
                    clean_err = "Video is unavailable or has been removed."
                job.error_message = clean_err
                print(f"[Downloader] Error downloading {job.url}: {traceback.format_exc()}")

download_manager = DownloadManager()

