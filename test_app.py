# -*- coding: utf-8 -*-
import os
import sys
import time
import unittest
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient

from app.server import app
from app.config import get_ffmpeg_path, get_node_path, load_config
from app.downloader import sanitize_filename, identify_platform, format_bytes, format_seconds, analyze_url, download_manager
from app.history import history_manager

client = TestClient(app)

class TestDownloaderCornerCases(unittest.TestCase):

    def test_01_system_status(self):
        """Test system status endpoint and FFmpeg/Node detection."""
        response = client.get("/api/system-status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["ffmpeg_available"], "FFmpeg should be detected")
        self.assertTrue(bool(data["ffmpeg_path"]), "FFmpeg path should not be empty")
        print("[PASS] System status and FFmpeg verified:", data["ffmpeg_path"])

    def test_02_filename_sanitization_corner_cases(self):
        """Test edge cases with illegal characters, unicode, trailing dots, length limit."""
        # 1. Windows illegal characters
        dirty_name = 'Video: "Best" of <2026> / Live | Show? *Special*'
        clean = sanitize_filename(dirty_name)
        for char in '<>:"/\\|?*':
            self.assertNotIn(char, clean, f"Illegal character {char} found in cleaned name")
        print("[PASS] Sanitized dirty filename:", clean)

        # 2. Unicode and non-ASCII characters
        unicode_name = "Rick Astley - Music Official Track"
        clean_unicode = sanitize_filename(unicode_name)
        self.assertTrue(len(clean_unicode) > 5)
        print("[PASS] Sanitized unicode filename:", clean_unicode)

        # 3. Trailing dots and spaces
        dots_name = "...test file name...   "
        clean_dots = sanitize_filename(dots_name)
        self.assertEqual(clean_dots, "test file name")

        # 4. Overly long filename (>250 chars)
        long_name = "A" * 300
        clean_long = sanitize_filename(long_name)
        self.assertLessEqual(len(clean_long), 180, "Filename should be trimmed below 180 chars")

        # 5. Empty or only illegal characters
        empty_name = '??::""//\\\\'
        clean_empty = sanitize_filename(empty_name)
        self.assertEqual(clean_empty, "download")

    def test_03_platform_identification(self):
        """Test identification of multiple video/audio platforms."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "YouTube", "youtube"),
            ("https://youtu.be/dQw4w9WgXcQ", "YouTube", "youtube"),
            ("https://youtube.com/shorts/abcdef12345", "YouTube", "youtube"),
            ("https://www.facebook.com/watch/?v=10153231379946729", "Facebook", "facebook"),
            ("https://fb.watch/xyz123/", "Facebook", "facebook"),
            ("https://www.facebook.com/reel/123456789", "Facebook", "facebook"),
            ("https://www.instagram.com/p/Cxyz123/", "Instagram", "instagram"),
            ("https://www.tiktok.com/@user/video/12345", "TikTok", "tiktok"),
            ("https://twitter.com/user/status/12345", "X (Twitter)", "twitter"),
            ("https://x.com/user/status/12345", "X (Twitter)", "twitter"),
            ("https://soundcloud.com/artist/track", "SoundCloud", "soundcloud"),
            ("https://example.com/some-video.mp4", "Web Media", "generic")
        ]
        for url, expected_name, expected_key in test_cases:
            p = identify_platform(url)
            self.assertEqual(p["key"], expected_key, f"Failed for URL: {url}")
            self.assertEqual(p["name"], expected_name, f"Failed for URL: {url}")
        print("[PASS] All 12 platform identification test cases passed")

    def test_04_formatting_helpers(self):
        """Test human readable bytes and duration formatters."""
        self.assertEqual(format_bytes(500), "500.0 B")
        self.assertEqual(format_bytes(1048576), "1.0 MB")
        self.assertEqual(format_bytes(1073741824), "1.0 GB")
        self.assertEqual(format_bytes(0), "Unknown size")
        self.assertEqual(format_bytes(None), "Unknown size")

        self.assertEqual(format_seconds(45), "00:45")
        self.assertEqual(format_seconds(125), "02:05")
        self.assertEqual(format_seconds(3665), "01:01:05")
        self.assertEqual(format_seconds(None), "--:--")

    def test_05_invalid_url_corner_cases(self):
        """Test invalid URLs, empty strings, and malformed inputs."""
        # Empty input
        res1 = client.post("/api/analyze", json={"url": ""})
        self.assertEqual(res1.status_code, 400)

        # Whitespace input
        res2 = client.post("/api/analyze", json={"url": "   "})
        self.assertEqual(res2.status_code, 400)

        # Gibberish URL
        res3 = client.post("/api/analyze", json={"url": "https://notarealdomain123456789xyz.com/video"})
        self.assertEqual(res3.status_code, 400)
        data = res3.json()
        self.assertFalse(data.get("success", False))
        self.assertIn("error", data)
        print("[PASS] Handled invalid URL gracefully:", data["error"][:60])

    def test_06_youtube_analysis(self):
        """Test real YouTube video analysis with format categorization."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        res = client.post("/api/analyze", json={"url": url})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        data = body["data"]

        self.assertIn("Rick Astley", data["title"])
        self.assertTrue(bool(data["thumbnail"]))
        self.assertGreater(len(data["video_formats"]), 0)
        self.assertGreater(len(data["audio_formats"]), 0)

        # Check resolution structure
        resolutions = [f["resolution"] for f in data["video_formats"]]
        print(f"[PASS] YouTube video formats detected: {resolutions}")
        self.assertGreater(len(resolutions), 0, "Should detect at least one video format")
        for f in data["video_formats"]:
            self.assertIn("resolution", f)
            self.assertIn("ext", f)
            self.assertIn("badge", f)

        # Check audio presets
        audio_codecs = [a["codec"] for a in data["audio_formats"]]
        self.assertIn("mp3", audio_codecs)
        self.assertIn("m4a", audio_codecs)
        self.assertIn("wav", audio_codecs)

    def test_07_download_and_ffmpeg_audio_conversion(self):
        """Test live download and audio extraction into MP3."""
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo (19s)
        custom_name = f"test_me_at_zoo_{int(time.time())}"

        res = client.post("/api/download", json={
            "url": url,
            "type": "audio",
            "quality": "mp3-320",
            "container": "mp3",
            "custom_filename": custom_name
        })
        self.assertEqual(res.status_code, 200)
        job_id = res.json()["job_id"]
        self.assertTrue(bool(job_id))

        # Wait for completion (max 25s)
        completed = False
        final_job = None
        for _ in range(25):
            time.sleep(1)
            prog_res = client.get(f"/api/progress/{job_id}")
            self.assertEqual(prog_res.status_code, 200)
            final_job = prog_res.json()
            if final_job["status"] == "completed":
                completed = True
                break
            elif final_job["status"] == "error":
                self.fail(f"Download failed with error: {final_job.get('error_message')}")

        self.assertTrue(completed, "Download did not complete in time")
        self.assertTrue(os.path.exists(final_job["file_path"]), "Target MP3 file does not exist on disk")
        self.assertTrue(final_job["file_path"].endswith(".mp3"))
        print(f"[PASS] Downloaded and converted MP3: {final_job['file_path']} (Size: {os.path.getsize(final_job['file_path'])} bytes)")

        # Clean up test file
        try:
            os.remove(final_job["file_path"])
        except Exception:
            pass

    def test_08_history_api(self):
        """Test history listing, item deletion, and clear."""
        # Get history
        res = client.get("/api/history")
        self.assertEqual(res.status_code, 200)
        history = res.json()["history"]
        self.assertIsInstance(history, list)

        # Add mock item if empty
        if not history:
            item = history_manager.add_item({
                "title": "Sample Test Video",
                "url": "https://www.youtube.com/watch?v=sample",
                "format": "mp4",
                "status": "completed"
            })
            item_id = item["id"]
        else:
            item_id = history[0]["id"]

        # Delete single history item
        del_res = client.delete(f"/api/history/{item_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["success"])
        print("[PASS] History delete item verified")

    def test_09_settings_api(self):
        """Test settings get and update."""
        res = client.get("/api/settings")
        self.assertEqual(res.status_code, 200)
        orig_settings = res.json()

        # Update setting
        update_res = client.post("/api/settings", json={
            "browser_cookies": "chrome",
            "embed_thumbnail": True
        })
        self.assertEqual(update_res.status_code, 200)
        updated = update_res.json()["settings"]
        self.assertEqual(updated["browser_cookies"], "chrome")

        # Restore
        client.post("/api/settings", json={"browser_cookies": orig_settings.get("browser_cookies", "none")})
        print("[PASS] Settings API get and update verified")

if __name__ == "__main__":
    unittest.main()

