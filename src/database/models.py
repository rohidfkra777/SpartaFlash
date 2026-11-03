"""
SpartaFlash - Database Models.
Developer: Rohidfkra777
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class ProductionRecord:
    id: Optional[int] = None
    transaction_id: str = ""
    start_time: str = ""
    end_time: str = ""
    product_category: str = ""
    firmware_name: str = ""
    firmware_version: Optional[str] = None
    firmware_hash: str = ""
    target_chip: str = ""
    serial_port: str = ""
    baudrate: int = 460800
    mac_address: Optional[str] = None
    batch_name: Optional[str] = None
    equipment_id: Optional[str] = None
    result: str = "PENDING"  # PASS, FAIL, CANCELLED
    verification_status: str = "UNVERIFIED"  # VERIFIED, UNVERIFIED, FAILED
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    app_version: str = "1.0.0"
    operator_notes: Optional[str] = None
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: tuple, columns: list) -> "ProductionRecord":
        d = dict(zip(columns, row))
        return cls(
            id=d.get("id"),
            transaction_id=d.get("transaction_id", ""),
            start_time=d.get("start_time", ""),
            end_time=d.get("end_time", ""),
            product_category=d.get("product_category", ""),
            firmware_name=d.get("firmware_name", ""),
            firmware_version=d.get("firmware_version"),
            firmware_hash=d.get("firmware_hash", ""),
            target_chip=d.get("target_chip", ""),
            serial_port=d.get("serial_port", ""),
            baudrate=d.get("baudrate", 460800),
            mac_address=d.get("mac_address"),
            batch_name=d.get("batch_name"),
            equipment_id=d.get("equipment_id"),
            result=d.get("result", "PENDING"),
            verification_status=d.get("verification_status", "UNVERIFIED"),
            duration_seconds=float(d.get("duration_seconds", 0.0) or 0.0),
            error_message=d.get("error_message"),
            app_version=d.get("app_version", "1.0.0"),
            operator_notes=d.get("operator_notes"),
            created_at=d.get("created_at", "")
        )


@dataclass
class RegisteredDevice:
    id: Optional[int] = None
    mac_address: str = ""
    device_name: str = ""
    product_category: str = ""
    flashed_at: str = ""
    last_seen_at: Optional[str] = None
    ip_address: Optional[str] = None
    status: str = "OFFLINE"  # ONLINE, OFFLINE
    power_state: str = "UNKNOWN"  # ON, OFF, UNKNOWN
    voltage: float = 0.0
    current: float = 0.0
    power: float = 0.0
    energy: float = 0.0
    wifi_rssi: Optional[int] = None
    wifi_ssid: Optional[str] = None
    batch_name: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: tuple, columns: list) -> "RegisteredDevice":
        d = dict(zip(columns, row))
        return cls(
            id=d.get("id"),
            mac_address=d.get("mac_address", ""),
            device_name=d.get("device_name", ""),
            product_category=d.get("product_category", ""),
            flashed_at=d.get("flashed_at", ""),
            last_seen_at=d.get("last_seen_at"),
            ip_address=d.get("ip_address"),
            status=d.get("status", "OFFLINE"),
            power_state=d.get("power_state", "UNKNOWN"),
            voltage=float(d.get("voltage", 0.0) or 0.0),
            current=float(d.get("current", 0.0) or 0.0),
            power=float(d.get("power", 0.0) or 0.0),
            energy=float(d.get("energy", 0.0) or 0.0),
            wifi_rssi=d.get("wifi_rssi"),
            wifi_ssid=d.get("wifi_ssid"),
            batch_name=d.get("batch_name"),
            notes=d.get("notes")
        )
