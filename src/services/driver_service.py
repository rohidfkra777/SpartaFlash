"""
SpartaFlash - Windows USB-to-UART Driver Management Service.
Developer: Rohidfkra777

Checks Driver Store integrity (CH340, CP210x, FTDI) and provides 1-click
elevated driver installation for Windows workstations.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from src.config.constants import BASE_DIR

class DriverService:
    """Manages Windows USB-to-UART driver status and automated installation."""

    @classmethod
    def get_drivers_dir(cls) -> Path:
        # Check in BASE_DIR (if in dist or root)
        candidate1 = BASE_DIR / "drivers"
        if candidate1.exists():
            return candidate1
        # Check in parent
        candidate2 = BASE_DIR.parent / "drivers"
        if candidate2.exists():
            return candidate2
        return candidate1

    @classmethod
    def check_installed_drivers(cls) -> Dict[str, Any]:
        """
        Queries Windows Driver Store using pnputil.exe.
        Returns detection status for CP210x, CH340, and FTDI.
        """
        ch340_found = False
        cp210x_found = False
        ftdi_found = False

        try:
            res = subprocess.run(
                ["pnputil", "/enum-drivers"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            out_lower = res.stdout.lower()

            if "ch34" in out_lower or "wch.cn" in out_lower:
                ch340_found = True

            if "silabser" in out_lower or "slabvcp" in out_lower or "silicon labs" in out_lower:
                cp210x_found = True

            if "ftdi" in out_lower or "ftser2k" in out_lower:
                ftdi_found = True

        except Exception:
            pass

        return {
            "CH340": {
                "name": "WCH CH340 / CH341 USB-UART",
                "installed": ch340_found,
                "status": "Terpasang (Ready)" if ch340_found else "Belum Terpasang"
            },
            "CP210x": {
                "name": "Silicon Labs CP210x USB-UART Bridge",
                "installed": cp210x_found,
                "status": "Terpasang (Ready)" if cp210x_found else "Belum Terpasang"
            },
            "FTDI": {
                "name": "FTDI USB-UART UART Driver",
                "installed": ftdi_found,
                "status": "Terpasang (Ready)" if ftdi_found else "Belum Terpasang"
            },
            "all_primary_ready": (ch340_found or cp210x_found)
        }

    @classmethod
    def install_bundled_drivers(cls) -> Dict[str, Any]:
        """
        Installs bundled CH340 and CP210x drivers using pnputil /add-driver with elevated UAC privileges.
        """
        drivers_dir = cls.get_drivers_dir()
        ch340_inf = drivers_dir / "CH340" / "CH341SER" / "CH341SER.INF"
        cp210x_inf = drivers_dir / "CP210x" / "slabvcp.inf"

        inf_targets = []
        if ch340_inf.exists():
            inf_targets.append(str(ch340_inf.resolve()))
        if cp210x_inf.exists():
            inf_targets.append(str(cp210x_inf.resolve()))

        if not inf_targets:
            return {
                "success": False,
                "message": f"File installer driver tidak ditemukan di folder: {drivers_dir}"
            }

        # Build PowerShell command to run pnputil as administrator
        inf_args = " ".join([f'/add-driver \\"{inf}\\" /install' for inf in inf_targets])
        ps_cmd = f"Start-Process pnputil.exe -ArgumentList '{inf_args}' -Verb RunAs -Wait"

        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            # Re-check status
            status_after = cls.check_installed_drivers()
            return {
                "success": proc.returncode == 0,
                "message": "Instalasi driver selesai. Port serial sekarang siap digunakan.",
                "status": status_after
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Proses instalasi driver melebihi batas waktu (timeout)."
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Gagal menjalankan instalasi driver: {str(e)}"
            }

    @classmethod
    def auto_ensure_drivers_installed(cls, callback_on_installed=None) -> None:
        """
        Silently checks if CH340 or CP210x drivers are installed.
        If missing, prompts a clean one-click installer or executes background installation.
        """
        import threading

        def _worker():
            try:
                status = cls.check_installed_drivers()
                if not status.get("all_primary_ready", False):
                    # Drivers missing, trigger automated installation
                    res = cls.install_bundled_drivers()
                    if res.get("success") and callback_on_installed:
                        callback_on_installed()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True, name="DriverAutoChecker").start()
