"""
SpartaFlash - Firmware Validation Service.
Developer: Rohidfkra777

Validates firmware binaries, calculates SHA-256 hashes, inspects Espressif binary headers,
and verifies compatibility without modifying firmware files.
"""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from src.config.constants import FIRMWARE_DIR, ASSETS_FIRMWARE_DIR, BASE_DIR, PRODUCT_CONFIGS, get_secure_firmware_cache_dir
from src.utils.security_vault import SecurityVault

@dataclass
class FirmwareInfo:
    file_path: Path
    file_name: str
    exists: bool
    size_bytes: int = 0
    size_formatted: str = "0 B"
    sha256_hash: str = ""
    is_valid: bool = False
    header_magic: str = ""
    detected_chip_hint: str = "Unknown"
    version_hint: Optional[str] = None
    validation_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "file_name": self.file_name,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "size_formatted": self.size_formatted,
            "sha256_hash": self.sha256_hash,
            "is_valid": self.is_valid,
            "detected_chip_hint": self.detected_chip_hint,
            "version_hint": self.version_hint,
            "validation_message": self.validation_message,
        }

class FirmwareService:
    """Service to safely inspect, decrypt in-memory, and validate firmware files."""

    # Espressif chip magic identifiers in extended headers (ESP32 series)
    ESP_CHIP_IDS = {
        0x0000: "ESP32",
        0x0002: "ESP32-S2",
        0x0005: "ESP32-C3",
        0x0009: "ESP32-S3",
        0x000C: "ESP32-C2",
        0x000D: "ESP32-C6",
        0x0010: "ESP32-H2",
    }

    @staticmethod
    def format_size(bytes_count: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}" if unit != "B" else f"{bytes_count} B"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} TB"

    @classmethod
    def get_firmware_path(cls, product_category: str) -> Path:
        """
        Locates firmware with priority:
        1. Encrypted vault inside assets/firmware/*.alfa_enc (Embedded & Protected)
        2. Unencrypted fallback in firmware/ (Development mode)
        """
        # 1. Primary: Check encrypted vault in cache or assets/firmware/
        cache_dir = get_secure_firmware_cache_dir()
        vault_paths = [
            cache_dir / f"AlfaEnergy_{product_category}.factory.alfa_enc",
            cache_dir / f"AlfaEnergy_{product_category}.alfa_enc",
            ASSETS_FIRMWARE_DIR / f"AlfaEnergy_{product_category}.factory.alfa_enc",
            ASSETS_FIRMWARE_DIR / f"AlfaEnergy_{product_category}.alfa_enc",
            BASE_DIR.parent / "assets" / "firmware" / f"AlfaEnergy_{product_category}.factory.alfa_enc",
            BASE_DIR.parent / "assets" / "firmware" / f"AlfaEnergy_{product_category}.alfa_enc"
        ]
        for vp in vault_paths:
            if vp.exists():
                return vp

        # 2. Secondary: Check local development firmware folder
        config = PRODUCT_CONFIGS.get(product_category, {})
        default_name = config.get("default_firmware", f"AlfaEnergy_{product_category}.bin")
        path1 = FIRMWARE_DIR / default_name
        if path1.exists():
            return path1

        path2 = FIRMWARE_DIR.parent.parent / "firmware" / default_name
        if path2.exists():
            return path2

        return vault_paths[0]

    @classmethod
    def calculate_sha256(cls, file_path: Path) -> str:
        if SecurityVault.is_encrypted_vault_file(file_path):
            raw = SecurityVault.decrypt_file_bytes(file_path)
            return hashlib.sha256(raw).hexdigest()

        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def get_ephemeral_binary(cls, file_path: Path):
        """Returns a secure context manager providing a temporary decrypted binary path."""
        return SecurityVault.get_ephemeral_firmware(file_path)

    @classmethod
    def _inspect_bytes_header(cls, raw: bytes) -> Tuple[bool, str, str, Optional[str]]:
        """Inspects in-memory binary bytes for Espressif magic markers."""
        if len(raw) < 4:
            return False, "", "Corrupt / Empty Binary", None

        magic = raw[0]
        magic_hex = f"0x{magic:02X}"

        if magic != 0xE9:
            # Merged factory binary at offset 0x1000
            if len(raw) >= 0x1020 and raw[0x1000] == 0xE9:
                magic_hex = "0xE9 (@0x1000)"
                chip_hint = "ESP32"
                chip_id = raw[0x100C] | (raw[0x100D] << 8)
                if chip_id in cls.ESP_CHIP_IDS:
                    chip_hint = cls.ESP_CHIP_IDS[chip_id]
                return True, magic_hex, chip_hint, None

            # String scan
            sample = raw[:65536]
            detected_chip = "Raw Binary / Unknown"
            if b"ESP32-S3" in sample:
                detected_chip = "ESP32-S3"
            elif b"ESP32-C3" in sample:
                detected_chip = "ESP32-C3"
            elif b"ESP32" in sample:
                detected_chip = "ESP32"
            elif b"ESP8266" in sample or b"esp8266" in sample:
                detected_chip = "ESP8266"
            return True, magic_hex, detected_chip, None

        chip_hint = "ESP8266 / ESP32 Generic"
        if len(raw) >= 14:
            chip_id = raw[12] | (raw[13] << 8)
            if chip_id in cls.ESP_CHIP_IDS:
                chip_hint = cls.ESP_CHIP_IDS[chip_id]

        version_hint = None
        chunk = raw[:131072]
        for prefix in [b"v1.", b"v2.", b"v0.", b"AlfaEnergy-v", b"IDF_VER_"]:
            idx = chunk.find(prefix)
            if idx != -1:
                raw_str = chunk[idx:idx+32].split(b"\x00")[0]
                try:
                    clean_str = raw_str.decode("utf-8", errors="ignore").strip()
                    if len(clean_str) > 2:
                        version_hint = clean_str
                        break
                except Exception:
                    pass

        return True, magic_hex, chip_hint, version_hint

    @classmethod
    def inspect_espressif_header(cls, file_path: Path) -> Tuple[bool, str, str, Optional[str]]:
        """Inspects binary header from disk or encrypted vault."""
        try:
            if SecurityVault.is_encrypted_vault_file(file_path):
                raw = SecurityVault.decrypt_file_bytes(file_path)
                return cls._inspect_bytes_header(raw)

            with open(file_path, "rb") as f:
                header = f.read(131072)
                return cls._inspect_bytes_header(header)
        except Exception as e:
            return False, "", f"Error reading header: {str(e)}", None

    @classmethod
    def validate_firmware(cls, file_path: Path, expected_product: Optional[str] = None) -> FirmwareInfo:
        """Thoroughly inspects firmware file (plain or encrypted vault) without modifying it."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            product_hint = f" for {expected_product}" if expected_product else ""
            clean_name = path.name.replace(".alfa_enc", ".bin")
            return FirmwareInfo(
                file_path=path,
                file_name=clean_name,
                exists=False,
                is_valid=False,
                validation_message=(
                    f"Firmware binary not found: {clean_name}\n"
                    f"Secure vault asset is missing from installation."
                )
            )

        try:
            is_vault = SecurityVault.is_encrypted_vault_file(path)
            clean_name = path.name.replace(".alfa_enc", ".bin")

            if is_vault:
                raw_bytes = SecurityVault.decrypt_file_bytes(path)
                size = len(raw_bytes)
                sha256 = hashlib.sha256(raw_bytes).hexdigest()
                is_valid_header, magic_hex, chip_hint, version_hint = cls._inspect_bytes_header(raw_bytes)
                status_msg = "✓ Biner Terproteksi (AES-256 Encrypted Vault)"
            else:
                size = os.path.getsize(path)
                sha256 = cls.calculate_sha256(path)
                is_valid_header, magic_hex, chip_hint, version_hint = cls.inspect_espressif_header(path)
                status_msg = "Firmware verified. Valid binary structure."

            if size == 0:
                return FirmwareInfo(
                    file_path=path,
                    file_name=clean_name,
                    exists=True,
                    size_bytes=0,
                    size_formatted="0 B",
                    is_valid=False,
                    validation_message="Firmware payload is empty (0 bytes)."
                )

            if size < 4096:
                return FirmwareInfo(
                    file_path=path,
                    file_name=clean_name,
                    exists=True,
                    size_bytes=size,
                    size_formatted=cls.format_size(size),
                    is_valid=False,
                    validation_message=f"Firmware payload is suspiciously small ({size} bytes)."
                )

            return FirmwareInfo(
                file_path=path,
                file_name=clean_name,
                exists=True,
                size_bytes=size,
                size_formatted=cls.format_size(size),
                sha256_hash=sha256,
                is_valid=True,
                header_magic=magic_hex,
                detected_chip_hint=chip_hint,
                version_hint=version_hint,
                validation_message=status_msg
            )

        except Exception as e:
            return FirmwareInfo(
                file_path=path,
                file_name=path.name.replace(".alfa_enc", ".bin"),
                exists=True,
                is_valid=False,
                validation_message=f"Error validating firmware vault: {str(e)}"
            )
