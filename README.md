# ⚡ Faydrop • Ultra-Modern Video & Audio Downloader

> **Designed & Developed by Faysal**  
> *A high-performance personal media downloader application built with a mobile-first Cyber-Dark UI, smooth ambient animations, live streaming progress tracking, and automatic multi-stream FFmpeg multiplexing.*

Supports **YouTube** (4K/60fps, 1080p Full HD, Shorts, Music), **Facebook** (Watch, Reels, Videos), **Instagram**, **TikTok**, **Twitter/X**, **Reddit**, **SoundCloud**, and 1000+ web platforms.

---

## ✨ Features

- **Futuristic Cyber-Dark UI & Faydrop Brand Identity**:
  - Custom purple gradient brand logo with high-res transparent PNG & favicon integration.
  - Deep space theme with glowing neon purple/cyan accents, frosted glassmorphism (`backdrop-filter: blur`), and animated ambient mesh glows.
  - Interactive platform detection that changes icons and colors as you paste links.
  - Smooth micro-interactions, responsive format cards, and animated gradient stripes on progress bars.
  - Toast notification system for instant feedback.

- **Dual Extraction Engine**:
  - **🎬 Video Formats**: 4K Ultra HD (2160p), 2K Quad HD (1440p), 1080p Full HD, 720p HD, 480p, 360p.
    - Automatic audio/video multiplexing via FFmpeg 7.1.
    - Choose between **MP4** (universal compatibility) and **MKV**.
  - **🎵 Audio Formats**: MP3 320 kbps (High Fidelity), 256 kbps, 192 kbps, 128 kbps, M4A (Original AAC), Lossless WAV, and Hi-Res FLAC.
    - Automatic ID3 tag embedding (Artist, Title, Album) and embedded cover art.

- **Real-Time Download Tracking**:
  - Live percentage progress bar, download speed (`MB/s`), total size, and estimated time remaining (ETA).
  - Status phases: Connecting -> Downloading -> FFmpeg Multiplexing / Converting -> Complete.
  - Cancel active downloads anytime with 1 click.

- **Local & Browser Dual Delivery**:
  - **Direct to Disk**: Files are saved directly into your local Downloads directory (`~/Downloads/DownloaderApp`).
  - **Play / Reveal**: 1-click **Play** (opens in default Windows media player) and **Show in Folder** (opens Windows File Explorer).
  - **Browser Download**: Download directly into your browser's download manager via streaming endpoint.

- **Corner Cases Handled**:
  - **YouTube Bot Bypass**: Multi-client fallback (`tv_embedded`, `android`, `ios`, `mweb`, `web`) and Node.js JavaScript runtime detection.
  - **Facebook Links**: Supports `facebook.com/watch/?v=...`, `facebook.com/.../videos/...`, `fb.watch/...`, and reels.
  - **Unicode & Special Character Titles**: Strips invalid Windows path characters (`\ / : * ? " < > |`) and safely sanitizes filenames.
  - **Name Collision Prevention**: Automatically indexes duplicate filenames.
  - **Private / Restricted Content**: Optional browser cookies integration (Chrome, Edge, Brave, Firefox) in Settings.
  - **Embedded FFmpeg**: Uses bundled FFmpeg 7.1 from `imageio-ffmpeg` without requiring manual system environment PATH setup.

---

## 🚀 Quick Start

### 1. Launch via Batch File (Windows)
Double click `run.bat` or run:
```powershell
.\run.bat
```

### 2. Launch via Python CLI
```powershell
py main.py
```
OmniStream will launch the local server and automatically open your default web browser to `http://localhost:5000`.

---

## 🛠 Technology Stack

- **Backend**: Python 3.13, FastAPI, Uvicorn, yt-dlp, FFmpeg 7.1 (via imageio-ffmpeg).
- **Frontend**: HTML5, Tailwind CSS, Lucide Icons, Vanilla JavaScript, Server-Sent Events (SSE).
- **Packaging**: Zero external setup required on Windows; auto-detects ports and runs seamlessly.

# faydrop
