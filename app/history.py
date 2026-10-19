import os
import json
import time
import uuid
from pathlib import Path
from app.config import HISTORY_FILE

class HistoryManager:
    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = history_file
        self._ensure_file()

    def _ensure_file(self):
        if not self.history_file.exists():
            try:
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception as e:
                print(f"[History] Error creating history file: {e}")

    def get_all(self) -> list:
        try:
            if not self.history_file.exists():
                return []
            with open(self.history_file, "r", encoding="utf-8") as f:
                items = json.load(f)
            
            # Check if files still exist on disk
            for item in items:
                filepath = item.get("file_path", "")
                item["file_exists"] = bool(filepath and os.path.exists(filepath))
            
            # Return newest first
            return sorted(items, key=lambda x: x.get("timestamp", 0), reverse=True)
        except Exception as e:
            print(f"[History] Error reading history: {e}")
            return []

    def add_item(self, item: dict) -> dict:
        items = self.get_all()
        if "id" not in item:
            item["id"] = str(uuid.uuid4())[:8]
        if "timestamp" not in item:
            item["timestamp"] = int(time.time())
        if "created_at" not in item:
            item["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Avoid duplicate ids
        items = [i for i in items if i.get("id") != item["id"]]
        items.insert(0, item)

        # Keep max 200 items
        items = items[:200]
        self._save(items)
        return item

    def update_item(self, item_id: str, updates: dict) -> bool:
        items = self.get_all()
        found = False
        for item in items:
            if item.get("id") == item_id:
                item.update(updates)
                found = True
                break
        if found:
            self._save(items)
        return found

    def delete_item(self, item_id: str, delete_file: bool = False) -> bool:
        items = self.get_all()
        target = next((i for i in items if i.get("id") == item_id), None)
        if not target:
            return False

        if delete_file and target.get("file_path") and os.path.exists(target["file_path"]):
            try:
                os.remove(target["file_path"])
            except Exception as e:
                print(f"[History] Failed to delete file {target['file_path']}: {e}")

        items = [i for i in items if i.get("id") != item_id]
        self._save(items)
        return True

    def clear_all(self) -> bool:
        try:
            self._save([])
            return True
        except Exception:
            return False

    def _save(self, items: list):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[History] Error saving history: {e}")

history_manager = HistoryManager()

