import os
import json
import shutil
import sys
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = BASE_DIR / "static"
CONFIG_FILE = BASE_DIR / "config.json"
HISTORY_FILE = BASE_DIR / "history.json"
ADMIN_HISTORY_FILE = BASE_DIR / "admin_history.json"
USER_HISTORY_FILE = BASE_DIR / "user_history.json"

# Temp downloads directory (for saving server space & web delivery)
TEMP_DOWNLOAD_DIR = BASE_DIR / "temp_downloads"
TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Default Downloads directory: User's Downloads/Faydrop
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "Faydrop"
DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "download_dir": str(DEFAULT_DOWNLOAD_DIR),
    "default_video_quality": "best",
    "default_audio_format": "mp3",
    "default_audio_bitrate": "320",
    "embed_thumbnail": True,
    "embed_metadata": True,
    "browser_cookies": "none",  # none, chrome, edge, firefox, brave
    "concurrent_downloads": 3,
    "port": 5000
}

def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception as e:
            print(f"[Config] Error loading config.json, using defaults: {e}")
    else:
        save_config(config)
    return config

def save_config(config: dict) -> bool:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"[Config] Error saving config.json: {e}")
        return False

def get_ffmpeg_dir() -> str:
    """Returns directory containing both FFmpeg and FFprobe executables."""
    # 1. Check static_ffmpeg (contains full ffmpeg + ffprobe suite)
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        ffmpeg, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        if ffmpeg and os.path.exists(ffmpeg):
            return str(Path(ffmpeg).parent)
    except Exception:
        pass

    # 2. Check system PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return str(Path(sys_ffmpeg).parent)

    # 3. Check imageio_ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return str(Path(exe).parent)
    except Exception:
        pass

    return ""

def get_ffmpeg_path() -> str:
    """Detects and returns FFmpeg executable path."""
    # 1. Check static_ffmpeg
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        ffmpeg, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        if ffmpeg and os.path.exists(ffmpeg):
            return ffmpeg
    except Exception:
        pass

    # 2. Check imageio_ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_exe and os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
    except Exception:
        pass

    # 3. Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # 4. Check common Windows paths
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    return ""

def get_node_path() -> str:
    """Detects Node.js path for yt-dlp JavaScript runtime."""
    node_exe = shutil.which("node")
    return node_exe or ""

