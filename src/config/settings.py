"""
SpartaFlash - Settings Manager.
Developer: Rohidfkra777
"""

import json
from pathlib import Path
from typing import Any, Dict
from src.config.constants import BASE_DIR, PRODUCT_PLUG

SETTINGS_FILE = BASE_DIR / "config" / "app_settings.json"

DEFAULT_SETTINGS = {
    "default_product": PRODUCT_PLUG,
    "default_baudrate": 460800,
    "auto_verify": True,
    "require_safety_acknowledgement": True,
    "batch_name_prefix": "BATCH-ALFA-",
    "operator_name": "Operator-1",
    "dark_mode": True,
    "verify_flash_write": True,
    "erase_before_flash": True,
    "chip_auto_detect": True,
    "custom_baudrate_enabled": False,
    "play_sound_on_completion": True,
}

class SettingsManager:
    def __init__(self, filepath: Path = SETTINGS_FILE):
        self.filepath = filepath
        self.settings: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings = {**DEFAULT_SETTINGS, **data}
                    return self.settings
            except Exception:
                self.settings = DEFAULT_SETTINGS.copy()
        else:
            self.settings = DEFAULT_SETTINGS.copy()
            self.save()
        return self.settings

    def save(self) -> bool:
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save()

# Global singleton
settings_manager = SettingsManager()
