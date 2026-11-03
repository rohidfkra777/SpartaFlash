"""
SpartaFlash - Cloud OTA Firmware Distribution Service.
Developer: Rohidfkra777

Connects to GitHub Pages CDN (https://buildingprocess25.github.io/AlfaEnergyFirmware/firmware/),
inspects binary updates via HTTP HEAD (Last-Modified / Content-Length / ETag),
downloads the latest firmware binaries, validates Espressif magic headers in-memory,
and encrypts them immediately into the local security vault (.alfa_enc) with zero plaintext leak.
"""

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Callable

from src.config.constants import (
    CLOUD_FIRMWARE_URLS,
    get_secure_firmware_cache_dir,
    PRODUCT_CONFIGS,
    PRODUCT_PLUG,
    PRODUCT_CT,
)
from src.utils.security_vault import SecurityVault

logger = logging.getLogger("AlfaEnergyFlasher")

USER_AGENT = "AlfaEnergyFlasher/1.0.0 (Production Workstation)"

class CloudFirmwareService:
    """Manages cloud firmware synchronizations and automatic security vault encryption."""

    METADATA_FILENAME = "cloud_sync_metadata.json"

    @classmethod
    def get_metadata_path(cls) -> Path:
        return get_secure_firmware_cache_dir() / cls.METADATA_FILENAME

    @classmethod
    def load_metadata(cls) -> Dict[str, Any]:
        p = cls.get_metadata_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to read cloud metadata: {e}")
        return {"files": {}, "last_checked": None}

    @classmethod
    def save_metadata(cls, meta: Dict[str, Any]) -> None:
        p = cls.get_metadata_path()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save cloud sync metadata: {e}")

    @classmethod
    def check_remote_status(cls, filename: str, timeout: float = 6.0) -> Tuple[bool, Dict[str, Any]]:
        """Sends HTTP HEAD request to check availability and metadata of a cloud binary."""
        url = CLOUD_FIRMWARE_URLS.get(filename)
        if not url:
            return False, {"error": f"Unknown firmware key: {filename}"}

        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    headers = resp.headers
                    cl = headers.get("Content-Length")
                    lm = headers.get("Last-Modified")
                    etag = headers.get("ETag")
                    return True, {
                        "url": url,
                        "status": 200,
                        "content_length": int(cl) if cl else 0,
                        "last_modified": lm,
                        "etag": etag,
                    }
        except Exception as e:
            logger.debug(f"HEAD check failed for {url}: {e}")
            return False, {"url": url, "error": str(e)}

        return False, {"url": url, "error": "Non-200 HTTP status"}

    @classmethod
    def check_for_updates(cls, product_category: Optional[str] = None) -> Dict[str, Any]:
        """
        Inspects cloud repository for available updates compared to local cache.
        Returns dictionary with online status, files needing update, and metadata.
        """
        meta = cls.load_metadata()
        cached_files = meta.get("files", {})

        targets = list(CLOUD_FIRMWARE_URLS.keys())
        if product_category:
            prefix = f"AlfaEnergy_{product_category}"
            targets = [t for t in targets if t.startswith(prefix)]

        updates_available = []
        is_online = False
        summary_details = {}

        for filename in targets:
            ok, info = cls.check_remote_status(filename)
            if ok:
                is_online = True
                cached = cached_files.get(filename, {})
                remote_lm = info.get("last_modified")
                remote_size = info.get("content_length", 0)

                # Check if local encrypted vault exists on disk
                stem = filename.replace(".bin", "")
                enc_file = get_secure_firmware_cache_dir() / f"{stem}.alfa_enc"

                needs_download = False
                if not enc_file.exists():
                    needs_download = True
                elif cached.get("last_modified") != remote_lm:
                    needs_download = True
                elif cached.get("content_length") != remote_size:
                    needs_download = True

                info["needs_download"] = needs_download
                summary_details[filename] = info
                if needs_download:
                    updates_available.append(filename)
            else:
                summary_details[filename] = info

        meta["last_checked"] = datetime.now().isoformat()
        cls.save_metadata(meta)

        return {
            "is_online": is_online,
            "has_updates": len(updates_available) > 0,
            "updates": updates_available,
            "details": summary_details,
        }

    @classmethod
    def download_and_encrypt(
        cls,
        filename: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        timeout: float = 30.0,
    ) -> Tuple[bool, str]:
        """
        Downloads binary directly into memory, validates header,
        encrypts into .alfa_enc vault, and saves atomically.
        """
        url = CLOUD_FIRMWARE_URLS.get(filename)
        if not url:
            return False, f"Unknown firmware key: {filename}"

        if progress_callback:
            progress_callback(10, f"Menghubungkan ke Cloud CDN ({filename})...")

        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    return False, f"Server HTTP status {resp.status}"

                total_size = int(resp.headers.get("Content-Length", 0))
                last_modified = resp.headers.get("Last-Modified")
                etag = resp.headers.get("ETag")

                downloaded = bytearray()
                chunk_size = 65536
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    downloaded.extend(chunk)
                    if total_size > 0 and progress_callback:
                        pct = min(85, int((len(downloaded) / total_size) * 75) + 10)
                        progress_callback(pct, f"Mengunduh {filename} ({len(downloaded) // 1024} KB)...")

                raw_bytes = bytes(downloaded)

        except urllib.error.URLError as e:
            return False, f"Gagal terhubung ke cloud: {e.reason}"
        except Exception as e:
            return False, f"Error unduh: {e}"

        # In-Memory Validation
        if len(raw_bytes) < 100_000:
            return False, f"Ukuran binary tidak valid ({len(raw_bytes)} bytes terlalu kecil)"

        magic = raw_bytes[0]
        if magic != 0xE9:
            # Merged factory binary at offset 0x1000
            if not (len(raw_bytes) >= 0x1020 and raw_bytes[0x1000] == 0xE9):
                return False, f"Espressif magic header 0xE9 tidak ditemukan pada {filename}"

        if progress_callback:
            progress_callback(88, f"Mengenkripsi {filename} ke dalam Vault...")

        # Encrypt into authenticated ciphertext
        try:
            enc_data = SecurityVault.encrypt_bytes(raw_bytes)
        except Exception as e:
            return False, f"Gagal enkripsi: {e}"

        # Atomic file write to cache directory
        cache_dir = get_secure_firmware_cache_dir()
        stem = filename.replace(".bin", "")
        dest_path = cache_dir / f"{stem}.alfa_enc"
        tmp_path = cache_dir / f"{stem}.tmp_enc"

        try:
            tmp_path.write_bytes(enc_data)
            if dest_path.exists():
                dest_path.unlink()
            tmp_path.rename(dest_path)
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            return False, f"Gagal menyimpan vault lokal: {e}"

        # Update metadata
        meta = cls.load_metadata()
        if "files" not in meta:
            meta["files"] = {}
        meta["files"][filename] = {
            "last_modified": last_modified,
            "content_length": len(raw_bytes),
            "etag": etag,
            "synced_at": datetime.now().isoformat(),
            "vault_path": str(dest_path),
        }
        cls.save_metadata(meta)

        if progress_callback:
            progress_callback(100, f"Selesai! {filename} terenkripsi di vault.")

        logger.info(f"Successfully downloaded and encrypted cloud firmware: {filename} -> {dest_path.name}")
        return True, f"Sukses sinkronisasi {filename}"

    @classmethod
    def sync_product(
        cls,
        product_category: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[bool, str]:
        """Synchronizes firmware binaries for a specific product category (Plug or CT)."""
        config = PRODUCT_CONFIGS.get(product_category, {})
        default_fw = config.get("default_firmware", f"AlfaEnergy_{product_category}.factory.bin")
        files = [default_fw]
        total = len(files)
        successes = 0
        messages = []

        for idx, fn in enumerate(files):
            def sub_callback(pct, msg):
                if progress_callback:
                    overall = int(((idx + (pct / 100)) / total) * 100)
                    progress_callback(overall, msg)

            ok, msg = cls.download_and_encrypt(fn, sub_callback)
            if ok:
                successes += 1
            messages.append(f"{fn}: {'OK' if ok else msg}")

        is_all_ok = successes == total
        summary = " | ".join(messages)
        return is_all_ok, summary
