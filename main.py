import os
import sys
import time
import socket
import webbrowser
import threading
import argparse
from pathlib import Path
import uvicorn

from app.config import load_config, get_ffmpeg_path, DEFAULT_DOWNLOAD_DIR

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def find_available_port(start_port: int = 5000, max_attempts: int = 10) -> int:
    port = start_port
    for _ in range(max_attempts):
        if not is_port_in_use(port):
            return port
        port += 1
    return start_port

def open_browser_delayed(url: str, delay: float = 1.0):
    def _open():
        time.sleep(delay)
        print(f"\n[Faydrop] Opening browser at {url} ...")
        webbrowser.open(url)
    t = threading.Thread(target=_open, daemon=True)
    t.start()

def main():
    parser = argparse.ArgumentParser(description="Faydrop Video & Audio Downloader by Faysal")
    parser.add_argument("--port", type=int, default=0, help="Server port (default: 5000 or $PORT)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically")
    parser.add_argument("--host", type=str, default="", help="Host address (default: 127.0.0.1 or 0.0.0.0 in cloud)")
    args = parser.parse_args()

    config = load_config()
    
    # Priority: CLI argument -> ENV $PORT -> config.json -> default 5000
    env_port = int(os.environ.get("PORT", 0)) if os.environ.get("PORT") else 0
    chosen_port = args.port or env_port or config.get("port", 5000)
    
    # In cloud environments (PORT is set or --host passed), bind to 0.0.0.0
    host = args.host or ("0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")

    if not os.environ.get("PORT") and is_port_in_use(chosen_port, host):
        alt_port = find_available_port(chosen_port + 1)
        print(f"[Faydrop] Port {chosen_port} is busy, switching to port {alt_port}")
        chosen_port = alt_port

    ffmpeg_path = get_ffmpeg_path()

    print("=" * 65)
    print("  ⚡ Faydrop • Video & Audio Downloader by Faysal ⚡")
    print("=" * 65)
    print(f"  • Web UI:        http://{host}:{chosen_port}")
    print(f"  • Downloads Dir: {config.get('download_dir', DEFAULT_DOWNLOAD_DIR)}")
    print(f"  • FFmpeg Engine: {'Online (' + ffmpeg_path + ')' if ffmpeg_path else 'Not Detected'}")
    print("=" * 65)

    if not args.no_browser and not os.environ.get("PORT"):
        open_browser_delayed(f"http://{host}:{chosen_port}")

    # Run Uvicorn server
    uvicorn.run(
        "app.server:app",
        host=host,
        port=chosen_port,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()

