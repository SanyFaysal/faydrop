import os
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import (
    HISTORY_FILE,
    ADMIN_HISTORY_FILE,
    USER_HISTORY_FILE,
    TEMP_DOWNLOAD_DIR,
    DEFAULT_DOWNLOAD_DIR
)

def format_bytes_stat(bytes_num: Optional[float]) -> str:
    if not bytes_num or bytes_num <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while bytes_num >= 1024 and i < len(units) - 1:
        bytes_num /= 1024.0
        i += 1
    return f"{bytes_num:.1f} {units[i]}"

class HistoryManager:
    def __init__(self):
        self.user_history_file = USER_HISTORY_FILE
        self.admin_history_file = ADMIN_HISTORY_FILE
        self._ensure_files()

    def _ensure_files(self):
        if not self.user_history_file.exists():
            try:
                # Map of device_id -> list of items
                with open(self.user_history_file, "w", encoding="utf-8") as f:
                    json.dump({}, f)
            except Exception as e:
                print(f"[History] Error creating user history file: {e}")

        if not self.admin_history_file.exists():
            try:
                # List of all admin audit items
                with open(self.admin_history_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception as e:
                print(f"[History] Error creating admin history file: {e}")

    def _load_user_history_map(self) -> Dict[str, List[dict]]:
        try:
            if not self.user_history_file.exists():
                return {}
            with open(self.user_history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[History] Error reading user history: {e}")
            return {}

    def _save_user_history_map(self, data: Dict[str, List[dict]]):
        try:
            with open(self.user_history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[History] Error saving user history: {e}")

    def _load_admin_history(self) -> List[dict]:
        try:
            if not self.admin_history_file.exists():
                return []
            with open(self.admin_history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[History] Error reading admin history: {e}")
            return []

    def _save_admin_history(self, items: List[dict]):
        try:
            with open(self.admin_history_file, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[History] Error saving admin history: {e}")

    def add_item(self, item: dict, device_id: str = "guest_default") -> dict:
        """Adds download record to both user-specific history and permanent admin audit history."""
        device_id = device_id.strip() if device_id else "guest_default"
        if "id" not in item:
            item["id"] = str(uuid.uuid4())[:8]
        if "timestamp" not in item:
            item["timestamp"] = int(time.time())
        if "created_at" not in item:
            item["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        item["device_id"] = device_id

        # 1. Update user-specific history
        user_map = self._load_user_history_map()
        user_items = user_map.get(device_id, [])
        user_items = [i for i in user_items if i.get("id") != item["id"]]
        user_items.insert(0, item)
        # Cap per user to 50
        user_map[device_id] = user_items[:50]
        self._save_user_history_map(user_map)

        # 2. Update permanent admin audit history (pure lightweight text metadata)
        admin_items = self._load_admin_history()
        # Create lightweight copy without local absolute system paths
        admin_entry = {
            "id": item["id"],
            "device_id": device_id,
            "title": item.get("title", "Untitled Media"),
            "url": item.get("url", ""),
            "platform": item.get("platform", {}).get("name", "Web") if isinstance(item.get("platform"), dict) else str(item.get("platform") or "Web"),
            "platform_key": item.get("platform", {}).get("key", "generic") if isinstance(item.get("platform"), dict) else "generic",
            "type": item.get("type", "video"),
            "format": item.get("format", "mp4"),
            "quality": item.get("quality", "best"),
            "file_size": item.get("file_size", 0),
            "file_size_str": item.get("file_size_str", "Unknown"),
            "file_name": item.get("file_name", ""),
            "timestamp": item["timestamp"],
            "created_at": item["created_at"],
            "status": item.get("status", "completed")
        }
        admin_items = [i for i in admin_items if i.get("id") != item["id"]]
        admin_items.insert(0, admin_entry)
        # Keep up to 1000 items in admin log
        admin_items = admin_items[:1000]
        self._save_admin_history(admin_items)

        return item

    def get_by_device(self, device_id: str) -> List[dict]:
        """Returns history only for the requested device ID."""
        device_id = device_id.strip() if device_id else "guest_default"
        user_map = self._load_user_history_map()
        items = user_map.get(device_id, [])

        # Check file exists on disk
        for item in items:
            filepath = item.get("file_path", "")
            item["file_exists"] = bool(filepath and os.path.exists(filepath))

        return sorted(items, key=lambda x: x.get("timestamp", 0), reverse=True)

    def delete_user_item(self, item_id: str, device_id: str, delete_file: bool = False) -> bool:
        """Removes an item from a user's private view without deleting from admin audit history."""
        device_id = device_id.strip() if device_id else "guest_default"
        user_map = self._load_user_history_map()
        items = user_map.get(device_id, [])
        target = next((i for i in items if i.get("id") == item_id), None)
        if not target:
            return False

        if delete_file and target.get("file_path") and os.path.exists(target["file_path"]):
            try:
                os.remove(target["file_path"])
            except Exception as e:
                print(f"[History] Failed to remove file: {e}")

        user_map[device_id] = [i for i in items if i.get("id") != item_id]
        self._save_user_history_map(user_map)
        return True

    def clear_user_history(self, device_id: str) -> bool:
        """Clears all history for a specific user/device. Admin audit history remains completely intact."""
        device_id = device_id.strip() if device_id else "guest_default"
        user_map = self._load_user_history_map()
        user_map[device_id] = []
        self._save_user_history_map(user_map)
        return True

    def get_admin_history(self, search: Optional[str] = None, filter_device: Optional[str] = None) -> List[dict]:
        """Returns all history across all users with optional filtering."""
        items = self._load_admin_history()
        if filter_device:
            items = [i for i in items if i.get("device_id") == filter_device]
        if search:
            q = search.lower().strip()
            items = [
                i for i in items 
                if q in i.get("title", "").lower() 
                or q in i.get("device_id", "").lower() 
                or q in i.get("platform", "").lower() 
                or q in i.get("url", "").lower()
            ]
        return sorted(items, key=lambda x: x.get("timestamp", 0), reverse=True)

    def clear_admin_history(self) -> bool:
        """Clears the admin audit log."""
        self._save_admin_history([])
        return True

    def get_admin_stats(self) -> dict:
        """Computes comprehensive admin statistics and storage metrics."""
        admin_items = self._load_admin_history()
        total_downloads = len(admin_items)
        unique_devices = len(set(i.get("device_id", "unknown") for i in admin_items if i.get("device_id")))

        total_bytes = sum(i.get("file_size", 0) for i in admin_items if isinstance(i.get("file_size"), (int, float)))

        # Calculate current physical disk usage of temp_downloads
        temp_disk_bytes = 0
        temp_files_count = 0
        if TEMP_DOWNLOAD_DIR.exists():
            for root, _, files in os.walk(TEMP_DOWNLOAD_DIR):
                for f in files:
                    try:
                        p = os.path.join(root, f)
                        temp_disk_bytes += os.path.getsize(p)
                        temp_files_count += 1
                    except Exception:
                        pass

        return {
            "total_downloads": total_downloads,
            "unique_devices": unique_devices,
            "total_data_processed": format_bytes_stat(total_bytes),
            "total_bytes": total_bytes,
            "temp_disk_usage": format_bytes_stat(temp_disk_bytes),
            "temp_disk_bytes": temp_disk_bytes,
            "temp_files_count": temp_files_count
        }

    def clean_temp_storage(self) -> dict:
        """Purges physical media files in temp_downloads to reclaim 100% server disk space."""
        freed_bytes = 0
        deleted_count = 0
        if TEMP_DOWNLOAD_DIR.exists():
            for root, _, files in os.walk(TEMP_DOWNLOAD_DIR):
                for f in files:
                    try:
                        p = os.path.join(root, f)
                        sz = os.path.getsize(p)
                        os.remove(p)
                        freed_bytes += sz
                        deleted_count += 1
                    except Exception as e:
                        print(f"[Storage] Could not remove {p}: {e}")

        return {
            "success": True,
            "deleted_files_count": deleted_count,
            "freed_bytes": freed_bytes,
            "freed_str": format_bytes_stat(freed_bytes)
        }

    # Backward compatibility helper
    def get_all(self) -> list:
        return self._load_admin_history()

    def clear_all(self) -> bool:
        self.clear_admin_history()
        self._save_user_history_map({})
        return True

history_manager = HistoryManager()
