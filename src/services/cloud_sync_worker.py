"""
SpartaFlash - Asynchronous Cloud Sync Worker Thread.
Developer: Rohidfkra777

Performs cloud firmware updates check and downloads in a background QThread
so the main workstation operator UI remains completely responsive and stutter-free.
"""

from typing import Optional, Dict, Any
from PySide6.QtCore import QThread, Signal

from src.services.cloud_firmware_service import CloudFirmwareService

class CloudSyncWorker(QThread):
    """Worker thread for asynchronous cloud firmware inspections and downloads."""

    sig_status = Signal(str)
    sig_progress = Signal(int, str)
    sig_finished = Signal(bool, str, dict)

    def __init__(
        self,
        mode: str = "check",
        product_category: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.mode = mode
        self.product_category = product_category
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self.mode == "check":
                self.sig_status.emit("Memeriksa repositori cloud firmware...")
                res = CloudFirmwareService.check_for_updates(self.product_category)
                if not res.get("is_online"):
                    self.sig_finished.emit(False, "Tidak dapat terhubung ke cloud (Mode Offline)", res)
                elif res.get("has_updates"):
                    count = len(res.get("updates", []))
                    self.sig_finished.emit(True, f"Ditemukan {count} pembaruan firmware di cloud", res)
                else:
                    self.sig_finished.emit(True, "Firmware lokal sudah versi terbaru (Up to Date)", res)

            elif self.mode == "sync_product":
                cat = self.product_category or "Plug"
                self.sig_status.emit(f"Menyinkronkan firmware {cat} dari Cloud CDN...")

                def progress_cb(pct: int, msg: str):
                    if not self._is_cancelled:
                        self.sig_progress.emit(pct, msg)

                ok, msg = CloudFirmwareService.sync_product(cat, progress_cb)
                self.sig_finished.emit(ok, msg, {"mode": "sync_product", "category": cat})

            elif self.mode == "sync_all":
                self.sig_status.emit("Menyinkronkan seluruh firmware dari Cloud...")
                from src.config.constants import CLOUD_FIRMWARE_URLS

                total = len(CLOUD_FIRMWARE_URLS)
                successes = 0
                results = {}

                for idx, fn in enumerate(CLOUD_FIRMWARE_URLS.keys()):
                    if self._is_cancelled:
                        break

                    def sub_cb(pct: int, msg: str):
                        overall = int(((idx + (pct / 100)) / total) * 100)
                        self.sig_progress.emit(overall, msg)

                    ok, msg = CloudFirmwareService.download_and_encrypt(fn, sub_cb)
                    if ok:
                        successes += 1
                    results[fn] = {"success": ok, "message": msg}

                is_ok = successes == total
                summary = f"Berhasil sinkronisasi {successes} dari {total} firmware"
                self.sig_finished.emit(is_ok, summary, results)

        except Exception as e:
            self.sig_finished.emit(False, f"Terjadi kesalahan koneksi cloud: {e}", {"error": str(e)})
