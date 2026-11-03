"""
SpartaFlash - Dependency Verification & Diagnostic Service.
Developer: Rohidfkra777
"""

import sys
import importlib
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class DependencyStatus:
    name: str
    required: bool
    is_installed: bool
    version: str = "Not Available"
    description: str = ""
    install_guide: str = ""

class DependencyService:
    """Verifies runtime modules and toolchains required for production flashing."""

    DEPENDENCIES = [
        {
            "name": "PySide6",
            "module": "PySide6",
            "required": True,
            "description": "Windows Industrial Qt6 GUI framework.",
            "install_guide": "pip install PySide6"
        },
        {
            "name": "esptool",
            "module": "esptool",
            "required": True,
            "description": "Espressif ROM bootloader flasher and chip diagnostic tool.",
            "install_guide": "pip install esptool"
        },
        {
            "name": "pySerial",
            "module": "serial",
            "required": True,
            "description": "Cross-platform serial port communication library.",
            "install_guide": "pip install pyserial"
        },
        {
            "name": "cryptography",
            "module": "cryptography",
            "required": False,
            "description": "Cryptographic operations for ESP32 secure boot / flash encryption.",
            "install_guide": "pip install cryptography"
        }
    ]

    @classmethod
    def check_all_dependencies(cls) -> Dict[str, Any]:
        results: List[DependencyStatus] = []
        all_required_met = True
        missing_required: List[str] = []

        for dep in cls.DEPENDENCIES:
            mod_name = dep["module"]
            display_name = dep["name"]
            is_installed = False
            version = "N/A"

            try:
                mod = importlib.import_module(mod_name)
                is_installed = True
                version = getattr(mod, "__version__", "Detected")
            except ImportError:
                is_installed = False
                if dep["required"]:
                    all_required_met = False
                    missing_required.append(display_name)

            status = DependencyStatus(
                name=display_name,
                required=dep["required"],
                is_installed=is_installed,
                version=version,
                description=dep["description"],
                install_guide=dep["install_guide"]
            )
            results.append(status)

        return {
            "all_required_met": all_required_met,
            "missing_required": missing_required,
            "dependencies": results,
            "python_version": sys.version.split()[0],
            "executable": sys.executable
        }
