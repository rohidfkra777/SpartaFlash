"""
SpartaFlash - Safety & Pre-Flash Protocol Service.
Developer: Rohidfkra777

Enforces industrial safety protocols, AC mains isolation checklists,
and hardware hazard warnings for technician & operator safety.
"""

from typing import List, Dict, Any

class SafetyService:
    """Safety checklists, warnings, and hardware validation protocols."""

    AC_MAINS_WARNING = """
    CRITICAL SAFETY WARNING - HIGH VOLTAGE RISK:
    --------------------------------------------------
    1. DISCONNECT AC MAINS POWER:
       Never connect the serial programmer while the device is plugged into AC mains (110V/220V).
       Failure to do so can result in fatal electric shock or destruction of programmer & PC!
    
    2. USE GALVANICALLY ISOLATED USB-TO-SERIAL:
       Ensure the USB-to-UART adapter is optically or galvanically isolated if working near line components.

    3. 3.3V LOGIC LEVEL ONLY:
       ESP8266 and ESP32 GPIOs and UART lines operate strictly at 3.3V logic.
       Connecting 5V UART signals directly may permanently damage the ESP chip.

    4. COMMON GROUND (GND):
       Ensure programmer GND is solidly connected before powering or applying signals.
    """

    SAFETY_CHECKLIST = [
        {
            "id": "ac_disconnected",
            "title": "AC Mains Disconnected",
            "description": "Device is completely disconnected from 220V AC / wall socket power.",
            "mandatory": True
        },
        {
            "id": "voltage_3v3",
            "title": "3.3V Logic Level Confirmed",
            "description": "Programmer VCC and UART logic level jumper is verified at 3.3V (NOT 5V).",
            "mandatory": True
        },
        {
            "id": "boot_mode",
            "title": "Bootloader Mode Ready",
            "description": "GPIO0 pulled to GND (or automatic DTR/RTS auto-reset circuit verified).",
            "mandatory": True
        },
        {
            "id": "firmware_match",
            "title": "Product Firmware Verified",
            "description": "Firmware binary selected matches current device model (Plug vs CT).",
            "mandatory": True
        }
    ]

    @classmethod
    def get_warning_dialog_text(cls, product_name: str) -> str:
        return (
            f"SAFETY VERIFICATION REQUIRED: {product_name}\n\n"
            "High Voltage Hazard Awareness:\n"
            "• Confirm device is NOT connected to AC power lines.\n"
            "• Use an approved 3.3V isolated USB-UART interface.\n"
            "• Follow AlfaEnergy Standard Operating Procedures (SOP).\n\n"
            "Do you confirm that all safety requirements are met and it is safe to proceed?"
        )
