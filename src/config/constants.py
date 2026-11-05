"""
SpartaFlash - Centralized Configuration and Constants.
Developer: Rohidfkra777
"""

import os
import sys
from pathlib import Path


# Application & Developer Identity
APP_NAME = "SpartaFlash"
APP_VERSION = "1.2.3"
APP_RELEASE_DATE = "2026-11-05"
APP_SUBTITLE = "Internal Firmware Flashing & Production Quality Control System"

DEVELOPER_NAME = "Rohidfkra777"
DEVELOPER_GITHUB = "https://github.com/rohidfkra777"
DEVELOPER_ROLE = "Software Developer & IoT Automation Engineer"
ORGANIZATION_NAME = "Enterprise IoT Systems"
ORGANIZATION_DEPT = "Building Maintenance & Energy System"
PROJECT_CONTEXT = "IoT & Energy Automation Internship"
COPYRIGHT_NOTICE = "© 2026 Rohidfkra777"
DEVELOPER_FOOTER_TEXT = "SpartaFlash Production Workstation | Developed by Rohidfkra777"

# Base Paths
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

FIRMWARE_DIR = BASE_DIR / "firmware"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"

# Persistent AppData Storage (Survives software updates, re-builds, and exe replacements)
PORTABLE_DATABASE_PATH = BASE_DIR / "database" / "production_history.db"

if (BASE_DIR / "portable.txt").exists():
    DATABASE_DIR = BASE_DIR / "database"
    DATABASE_PATH = PORTABLE_DATABASE_PATH
else:
    if sys.platform == "win32":
        app_data_env = os.environ.get("LOCALAPPDATA")
        if app_data_env:
            DATA_STORAGE_DIR = Path(app_data_env) / "AlfaEnergyFlasher"
        else:
            DATA_STORAGE_DIR = Path.home() / "AppData" / "Local" / "AlfaEnergyFlasher"
    else:
        DATA_STORAGE_DIR = Path.home() / ".local" / "share" / "AlfaEnergyFlasher"

    DATABASE_DIR = DATA_STORAGE_DIR / "database"
    DATABASE_PATH = DATABASE_DIR / "production_history.db"
ACTIVITY_DB_PATH = DATABASE_DIR / "user_activity.db"

# Assets & Branding
ASSETS_DIR = BASE_DIR / "assets"
if not ASSETS_DIR.exists() and (BASE_DIR / "_internal" / "assets").exists():
    ASSETS_DIR = BASE_DIR / "_internal" / "assets"

APP_ICON_PATH = ASSETS_DIR / "app_icon.png"
APP_ICON_ICO = ASSETS_DIR / "app_icon.ico"
LOGO_HORIZONTAL_PATH = ASSETS_DIR / "logo_horizontal.png"
ASSETS_FIRMWARE_DIR = ASSETS_DIR / "firmware"

# Cloud OTA Firmware Distribution (GitHub Pages CDN)
CLOUD_FIRMWARE_BASE_URL = "https://buildingprocess25.github.io/AlfaEnergyFirmware/firmware"
CLOUD_FIRMWARE_URLS = {
    "AlfaEnergy_Plug.factory.bin": f"{CLOUD_FIRMWARE_BASE_URL}/AlfaEnergy_Plug.factory.bin",
    "AlfaEnergy_CT.factory.bin": f"{CLOUD_FIRMWARE_BASE_URL}/AlfaEnergy_CT.factory.bin",
}

# MQTT Broker & Live Control Constants (Industrial IoT Infrastructure - Production Fleet)
DEFAULT_MQTT_BROKER = "103.127.99.241"
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_USER = "sparta-ganteng"
DEFAULT_MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
DEFAULT_MQTT_KEEPALIVE = 60
DEFAULT_MQTT_TOPIC_PREFIX = "AlfaEnergy"

def get_secure_firmware_cache_dir() -> Path:
    """Returns writable directory for encrypted firmware vault files."""
    try:
        ASSETS_FIRMWARE_DIR.mkdir(parents=True, exist_ok=True)
        test_file = ASSETS_FIRMWARE_DIR / ".write_test"
        test_file.touch()
        test_file.unlink()
        return ASSETS_FIRMWARE_DIR
    except Exception:
        import os
        local_app = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AlfaEnergyFlasher" / "firmware"
        local_app.mkdir(parents=True, exist_ok=True)
        return local_app

# Ensure runtime directories exist
for folder in [FIRMWARE_DIR, LOGS_DIR, REPORTS_DIR, DATABASE_DIR, ASSETS_DIR, ASSETS_FIRMWARE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Product Categories
PRODUCT_PLUG = "Plug"
PRODUCT_CT = "CT"

PRODUCT_CONFIGS = {
    PRODUCT_PLUG: {
        "display_name": "Sparta Smart Plug",
        "category": PRODUCT_PLUG,
        "default_firmware": "AlfaEnergy_Plug.factory.bin",
        "flash_baud": 460800,
        "flash_mode": "dio",
        "flash_freq": "40m",
        "description": "Smart Plug AC Energy Monitor & Relay Module (ESP32-C3)",
        "requires_ac_isolation_warning": True,
        "target_chip_display": "ESP32-C3",
        "supported_chips": ["ESP32-C3"],
        "default_address": "0x0",  # Merged factory binary writes from 0x0
        "power_voltage": "5V DC",
        "logic_voltage": "3.3V UART (Strict)",
        "wiring_guide": "Power: 5V DC | Logic: 3.3V UART"
    },
    PRODUCT_CT: {
        "display_name": "Sparta Smart CT",
        "category": PRODUCT_CT,
        "default_firmware": "AlfaEnergy_CT.factory.bin",
        "flash_baud": 460800,
        "flash_mode": "dio",
        "flash_freq": "40m",
        "description": "Multi-Channel Current Transformer Energy Monitoring System (ESP32 Dual Core)",
        "requires_ac_isolation_warning": True,
        "target_chip_display": "ESP32 Dual Core",
        "supported_chips": ["ESP32"],
        "default_address": "0x0",
        "power_voltage": "3.3V DC",
        "logic_voltage": "3.3V UART",
        "wiring_guide": "Power & Logic: Full 3.3V DC"
    }
}

# Production Flashing Statuses
STATUS_READY = "READY"
STATUS_CONNECTING = "CONNECTING"
STATUS_VALIDATING = "VALIDATING"
STATUS_CHIP_DETECTED = "CHIP_DETECTED"
STATUS_ERASING = "ERASING"
STATUS_FLASHING = "FLASHING"
STATUS_VERIFYING = "VERIFYING"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_CANCELLED = "CANCELLED"

# Default Flashing Baudrates
BAUD_RATES = [115200, 230400, 460800, 921600]
