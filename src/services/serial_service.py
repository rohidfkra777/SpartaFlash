"""
SpartaFlash - Serial Port Detection & Diagnostic Service.
Developer: Rohidfkra777
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import serial.tools.list_ports
import serial

@dataclass
class SerialPortInfo:
    device: str
    description: str
    hwid: str
    vid: Optional[int] = None
    pid: Optional[int] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    is_common_esp_adapter: bool = False
    adapter_chip_type: str = "Unknown"

    @property
    def display_name(self) -> str:
        if self.description and self.description != self.device:
            return f"{self.device} - {self.description}"
        return self.device

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "description": self.description,
            "hwid": self.hwid,
            "vid": f"0x{self.vid:04X}" if self.vid else None,
            "pid": f"0x{self.pid:04X}" if self.pid else None,
            "manufacturer": self.manufacturer,
            "serial_number": self.serial_number,
            "is_common_esp_adapter": self.is_common_esp_adapter,
            "adapter_chip_type": self.adapter_chip_type,
        }

class SerialService:
    """Service for discovering and checking serial ports."""

    # Common USB to Serial VID/PID combinations used for ESP flashing
    KNOWN_ADAPTERS = {
        (0x10C4, 0xEA60): "Silicon Labs CP210x",
        (0x10C4, 0xEA70): "Silicon Labs CP2105 Dual Port",
        (0x1A86, 0x7523): "WCH CH340",
        (0x1A86, 0x5523): "WCH CH341",
        (0x1A86, 0x55D4): "WCH CH9102",
        (0x0403, 0x6001): "FTDI FT232R",
        (0x0403, 0x6010): "FTDI FT2232 Dual Channel",
        (0x303A, 0x1001): "Espressif Built-in USB JTAG/Serial (ESP32-S3/C3)",
        (0x303A, 0x0002): "Espressif USB CDC",
    }

    @classmethod
    def list_ports(cls) -> List[SerialPortInfo]:
        """Scans and returns all available serial ports with diagnostic metadata."""
        ports = serial.tools.list_ports.comports()
        result: List[SerialPortInfo] = []

        for p in ports:
            is_esp_adapter = False
            chip_type = "Generic Serial Port"

            # Check VID/PID
            if p.vid is not None and p.pid is not None:
                key = (p.vid, p.pid)
                if key in cls.KNOWN_ADAPTERS:
                    is_esp_adapter = True
                    chip_type = cls.KNOWN_ADAPTERS[key]
                elif p.vid in [0x10C4, 0x1A86, 0x0403, 0x303A]:
                    is_esp_adapter = True
                    chip_type = f"Espressif Compatible (VID 0x{p.vid:04X})"

            # Also check description strings for common markers
            desc_lower = (p.description or "").lower()
            if any(k in desc_lower for k in ["ch340", "ch341", "cp210", "ftdi", "espressif", "usb-serial", "uart"]):
                is_esp_adapter = True
                if "ch340" in desc_lower:
                    chip_type = "WCH CH340"
                elif "cp210" in desc_lower:
                    chip_type = "Silicon Labs CP210x"
                elif "ftdi" in desc_lower:
                    chip_type = "FTDI UART"

            info = SerialPortInfo(
                device=p.device,
                description=p.description or "Unknown Serial Port",
                hwid=p.hwid or "",
                vid=p.vid,
                pid=p.pid,
                manufacturer=p.manufacturer,
                serial_number=p.serial_number,
                is_common_esp_adapter=is_esp_adapter,
                adapter_chip_type=chip_type,
            )
            result.append(info)

        # Sort with common ESP adapters first, then alphabetically by device name
        result.sort(key=lambda x: (not x.is_common_esp_adapter, x.device))
        return result

    @classmethod
    def test_port_availability(cls, port_name: str) -> Dict[str, Any]:
        """Tests if a port can be opened or if it's currently in use / inaccessible."""
        if not port_name:
            return {
                "available": False,
                "error": "No port selected.",
                "guide": "Please select a valid COM port from the dropdown."
            }

        try:
            ser = serial.Serial(port=port_name, timeout=1.0)
            ser.close()
            return {
                "available": True,
                "error": None,
                "guide": f"Port {port_name} is open and ready for flashing."
            }
        except serial.SerialException as e:
            err_str = str(e)
            if "PermissionError" in err_str or "Access is denied" in err_str:
                guide = (
                    f"Port {port_name} is currently locked or in use by another application.\n"
                    "Troubleshooting steps:\n"
                    "1. Close any serial monitors (Arduino IDE, PuTTY, PlatformIO, TeraTerm).\n"
                    "2. Check if another instance of SpartaFlash is running.\n"
                    "3. Unplug and replug the USB cable."
                )
            elif "FileNotFoundError" in err_str or "not found" in err_str.lower():
                guide = (
                    f"Port {port_name} was not found or was recently disconnected.\n"
                    "Troubleshooting steps:\n"
                    "1. Ensure the USB cable is securely connected.\n"
                    "2. Verify USB data cable functionality (avoid charge-only cables).\n"
                    "3. Click 'Scan Ports' to refresh."
                )
            else:
                guide = (
                    f"Could not open {port_name}: {err_str}\n"
                    "Troubleshooting steps:\n"
                    "1. Verify device drivers (CH340 / CP210x / FTDI).\n"
                    "2. Check Device Manager under 'Ports (COM & LPT)'.\n"
                    "3. Ensure the ESP module is receiving adequate power."
                )
            return {
                "available": False,
                "error": err_str,
                "guide": guide
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "guide": f"Unexpected error checking port {port_name}: {str(e)}"
            }
