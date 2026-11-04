
"""
SpartaFlash - ESP Flashing & Hardware Verification Service.
Developer: Rohidfkra777

Handles esptool execution, chip auto-detection, MAC address extraction,
real-time progress parsing, exit code verification, and process cancellation.
"""

import os
import re
import sys
import time
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple

from src.config.constants import (
    PRODUCT_CONFIGS,
    PRODUCT_PLUG,
    PRODUCT_CT,
    STATUS_READY,
    STATUS_CONNECTING,
    STATUS_VALIDATING,
    STATUS_CHIP_DETECTED,
    STATUS_ERASING,
    STATUS_FLASHING,
    STATUS_VERIFYING,
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_CANCELLED,
    APP_VERSION
)
from src.services.firmware_service import FirmwareService, FirmwareInfo
from src.services.serial_service import SerialService
from src.database.models import ProductionRecord
from src.database.db_manager import db_manager
from src.utils.logger import get_logger

@dataclass
class FlashProgress:
    percentage: int
    stage: str
    message: str
    is_terminal: bool = False

class FlasherService:
    """Core flashing engine communicating with esptool and recording production metrics."""

    def __init__(self):
        self.logger = get_logger()
        self._current_process: Optional[subprocess.Popen] = None
        self._is_cancelled = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._current_process is not None and self._current_process.poll() is None

    def cancel_flashing(self) -> None:
        """Safely terminates ongoing flashing process."""
        with self._lock:
            self._is_cancelled = True
            if self._current_process and self._current_process.poll() is None:
                self.logger.warning("Operator requested cancellation. Terminating flashing process...")
                try:
                    self._current_process.terminate()
                    # Allow 2 seconds graceful termination before force kill
                    time.sleep(1.0)
                    if self._current_process.poll() is None:
                        self._current_process.kill()
                except Exception as e:
                    self.logger.error(f"Error terminating process: {e}")

    @staticmethod
    def get_esptool_command() -> List[str]:
        """Returns the appropriate command to execute esptool."""
        # Use python -m esptool
        python_exe = sys.executable
        return [python_exe, "-m", "esptool"]

    def detect_chip_and_mac(self, port: str, baud: int = 115200) -> Dict[str, Any]:
        """
        Queries chip type, silicon features, and MAC address via esptool.
        Does NOT alter flash memory.
        """
        cmd = self.get_esptool_command() + [
            "--port", port,
            "--baud", str(baud),
            "chip_id"
        ]

        self.logger.info(f"Querying chip info on {port}...")
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=12,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            output = res.stdout + "\n" + res.stderr
            return self.parse_chip_id_output(output, res.returncode)

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "chip": "Unknown",
                "mac": None,
                "error": "Connection timed out. Check USB connection and bootloader mode (GPIO0)."
            }
        except Exception as e:
            return {
                "success": False,
                "chip": "Unknown",
                "mac": None,
                "error": str(e)
            }

    def read_mac_address(self, port: str, baud: int = 115200) -> Optional[str]:
        """Reads hardware MAC address directly from OTP / eFuse."""
        cmd = self.get_esptool_command() + [
            "--port", port,
            "--baud", str(baud),
            "read_mac"
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            text = res.stdout + "\n" + res.stderr
            match = re.search(r"MAC:\s*([0-9a-fA-F:]{17})", text)
            if match:
                return match.group(1).upper()
        except Exception:
            pass
        return None

    @staticmethod
    def parse_chip_id_output(output: str, returncode: int) -> Dict[str, Any]:
        """Extracts chip model, features, and MAC address from esptool output."""
        chip_detected = "Unknown"
        mac_address = None
        features = ""

        # Chip detection patterns
        # Priority 1: Match "Chip is ESP..." (e.g. "Chip is ESP32 (revision v3.0)", "Chip is ESP32-C3")
        chip_match = re.search(r"Chip is\s+(ESP[A-Za-z0-9\-]+)", output, re.IGNORECASE)
        
        # Priority 2: Match "Detecting chip type... ESP..." (ensuring it starts with ESP, ignoring 'Unsupported detection protocol')
        if not chip_match:
            chip_match = re.search(r"Detecting chip type\.\.\.\s*(?:Unsupported detection protocol[^\n]*\n\s*Detecting chip type\.\.\.\s*)?(ESP[A-Za-z0-9\-]+)", output, re.IGNORECASE)

        # Priority 3: Scan all 'Detecting chip type...' lines and take the last valid chip token
        if not chip_match:
            matches = re.findall(r"Detecting chip type\.\.\.\s+([A-Za-z0-9\-]+)", output)
            for m in reversed(matches):
                if m.upper() != "UNSUPPORTED" and m.upper().startswith("ESP"):
                    chip_detected = m.upper().strip()
                    break

        if chip_match:
            chip_detected = chip_match.group(1).upper().strip()
        elif "ESP32-C3" in output:
            chip_detected = "ESP32-C3"
        elif "ESP32-S3" in output:
            chip_detected = "ESP32-S3"
        elif "ESP32" in output:
            chip_detected = "ESP32"
        elif "ESP8266" in output:
            chip_detected = "ESP8266"

        # MAC address pattern
        mac_match = re.search(r"MAC:\s*([0-9a-fA-F:]{17})", output)
        if mac_match:
            mac_address = mac_match.group(1).upper()

        # Features pattern
        feat_match = re.search(r"Features:\s*(.+)", output)
        if feat_match:
            features = feat_match.group(1).strip()

        success = returncode == 0 and chip_detected != "Unknown"
        error_msg = "" if success else ("Failed to communicate with device bootloader.\n" + output[-300:])

        return {
            "success": success,
            "chip": chip_detected,
            "mac": mac_address,
            "features": features,
            "raw_output": output,
            "error": error_msg
        }

    @classmethod
    def validate_target_chip(
        cls,
        product_category: str,
        detected_chip: str,
        features: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Strict hardware compatibility verification.
        - Plug specifically requires ESP32-C3 (RISC-V).
        - CT specifically requires ESP32 Dual Core (Xtensa LX6).
        """
        chip_upper = detected_chip.upper().strip()
        features_lower = (features or "").lower()

        if product_category == PRODUCT_PLUG:
            # Must be ESP32-C3 specifically
            if re.search(r"\bESP32-?C3\b", chip_upper) or "ESP32C3" in chip_upper:
                return True, "Target chip terverifikasi: ESP32-C3"
            return False, (
                f"HARDWARE MISMATCH: Target chip terdeteksi '{detected_chip}', namun produk Sparta Smart Plug "
                f"mewajibkan chip 'ESP32-C3' (RISC-V architecture).\n"
                f"Flashing dibatalkan otomatis demi melindungi modul hardware dari kerusakan (bricking)."
            )

        elif product_category == PRODUCT_CT:
            # Must NOT be C3, S2, S3, C6, H2, or ESP8266
            if re.search(r"ESP32-?[CSH]\d", chip_upper) or "ESP8266" in chip_upper:
                return False, (
                    f"HARDWARE MISMATCH: Target chip terdeteksi '{detected_chip}', namun produk Sparta Smart CT "
                    f"mewajibkan chip 'ESP32 Dual Core' (Xtensa LX6 architecture).\n"
                    f"Flashing dibatalkan otomatis demi melindungi modul hardware dari kerusakan (bricking)."
                )

            # Must belong to ESP32 classic family
            if not chip_upper.startswith("ESP32"):
                return False, (
                    f"HARDWARE MISMATCH: Target chip terdeteksi '{detected_chip}', bukan keluarga chip 'ESP32 Dual Core'.\n"
                    f"Flashing dibatalkan otomatis demi melindungi modul hardware dari kerusakan (bricking)."
                )

            # Must not be single-core variant (e.g. ESP32-S0WD)
            if "single core" in features_lower:
                return False, (
                    f"HARDWARE MISMATCH: Target chip terdeteksi '{detected_chip}' dengan Single Core, sedangkan produk CT "
                    f"mewajibkan 'ESP32 Dual Core'.\n"
                    f"Flashing dibatalkan otomatis demi melindungi modul hardware dari kerusakan (bricking)."
                )

            return True, "Target chip terverifikasi: ESP32 Dual Core"

        # Fallback for generic configurations
        config = PRODUCT_CONFIGS.get(product_category, {})
        supported_chips = config.get("supported_chips", [])
        if not supported_chips or any(sup.lower() in detected_chip.lower() for sup in supported_chips):
            return True, f"Target chip terverifikasi: {detected_chip}"
        return False, f"HARDWARE MISMATCH: Target chip '{detected_chip}' tidak sesuai untuk {product_category}."

    def execute_flash_process(
        self,
        product_category: str,
        port: str,
        baudrate: int,
        custom_firmware_path: Optional[Path] = None,
        batch_name: Optional[str] = None,
        operator_notes: Optional[str] = None,
        verify_flash: bool = True,
        erase_all: bool = True,
        simulation_mode: bool = False,
        progress_callback: Optional[Callable[[FlashProgress], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ProductionRecord:
        """
        Executes complete flashing pipeline:
        1. Validation
        2. Chip detection
        3. Hardware compatibility check
        4. Erase & Flashing with real-time progress parsing
        5. Verification
        6. Database transaction recording
        """
        start_time_iso = time.strftime("%Y-%m-%d %H:%M:%S")
        start_mono = time.monotonic()
        tx_id = f"TX-{int(time.time())}-{os.urandom(3).hex().upper()}"

        record = ProductionRecord(
            transaction_id=tx_id,
            start_time=start_time_iso,
            product_category=product_category,
            serial_port=port,
            baudrate=baudrate,
            batch_name=batch_name,
            operator_notes=operator_notes,
            app_version=APP_VERSION,
            result=STATUS_FAIL,
            verification_status="UNVERIFIED",
            created_at=start_time_iso
        )

        config = PRODUCT_CONFIGS.get(product_category, {})

        def emit_log(msg: str):
            self.logger.info(msg)
            if log_callback:
                log_callback(msg)

        def emit_progress(pct: int, stage: str, text: str, is_term: bool = False):
            if progress_callback:
                progress_callback(FlashProgress(percentage=pct, stage=stage, message=text, is_terminal=is_term))

        self._is_cancelled = False

        # Step 1: Validate Firmware
        emit_progress(5, STATUS_VALIDATING, "Validating product firmware...")
        emit_log(f"Starting transaction {tx_id} for {product_category} on {port}@{baudrate}...")

        fw_path = custom_firmware_path or FirmwareService.get_firmware_path(product_category)
        fw_info = FirmwareService.validate_firmware(fw_path, product_category)

        record.firmware_name = fw_info.file_name
        record.firmware_hash = fw_info.sha256_hash
        record.firmware_version = fw_info.version_hint

        if not fw_info.exists or not fw_info.is_valid:
            err = f"Firmware validation failed: {fw_info.validation_message}"
            emit_log(f"ERROR: {err}")
            emit_progress(100, STATUS_FAIL, "Firmware Invalid", is_term=True)
            record.result = STATUS_FAIL
            record.error_message = err
            record.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
            record.duration_seconds = round(time.monotonic() - start_mono, 2)
            db_manager.insert_record(record)
            return record

        emit_log(f"Firmware: {fw_info.file_name} ({fw_info.size_formatted}) | SHA-256: {fw_info.sha256_hash[:16]}...")

        # Simulation Mode Handler (for automated tests or offline QA demonstration)
        if simulation_mode:
            return self._run_simulation(
                record, fw_info, start_mono, verify_flash, erase_all, emit_progress, emit_log
            )

        # Step 2: Validate Serial Port
        emit_progress(10, STATUS_CONNECTING, f"Testing serial port {port}...")
        port_test = SerialService.test_port_availability(port)
        if not port_test["available"]:
            err = f"Serial port unavailable: {port_test['error']}\n{port_test['guide']}"
            emit_log(f"ERROR: {err}")
            emit_progress(100, STATUS_FAIL, "Port Inaccessible", is_term=True)
            record.result = STATUS_FAIL
            record.error_message = err
            record.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
            record.duration_seconds = round(time.monotonic() - start_mono, 2)
            db_manager.insert_record(record)
            return record

        # Step 3: Connect and Detect Target Chip & MAC
        emit_progress(20, STATUS_CONNECTING, f"Connecting to bootloader on {port}...")
        emit_log("Querying target chip and MAC address...")
        chip_info = self.detect_chip_and_mac(port, baud=115200)

        if not chip_info["success"]:
            err = f"Failed to connect to ESP chip: {chip_info['error']}"
            emit_log(f"ERROR: {err}")
            emit_progress(100, STATUS_FAIL, "Chip Connection Failed", is_term=True)
            record.result = STATUS_FAIL
            record.error_message = err
            record.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
            record.duration_seconds = round(time.monotonic() - start_mono, 2)
            db_manager.insert_record(record)
            return record

        detected_chip = chip_info["chip"]
        mac_addr = chip_info["mac"]
        record.target_chip = detected_chip
        record.mac_address = mac_addr

        emit_log(f"Detected Chip: {detected_chip} | MAC: {mac_addr or 'N/A'}")
        if chip_info.get("features"):
            emit_log(f"Silicon Features: {chip_info['features']}")

        # Step 4: Hardware Compatibility Check (Strict Architecture Validation)
        is_supported, match_msg = self.validate_target_chip(
            product_category=product_category,
            detected_chip=detected_chip,
            features=chip_info.get("features")
        )

        if not is_supported:
            emit_log(f"CRITICAL: {match_msg}")
            emit_progress(100, STATUS_FAIL, "Hardware Mismatch", is_term=True)
            record.result = STATUS_FAIL
            record.error_message = match_msg
            record.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
            record.duration_seconds = round(time.monotonic() - start_mono, 2)
            db_manager.insert_record(record)
            return record

        emit_progress(30, STATUS_CHIP_DETECTED, f"{match_msg}: {detected_chip}")

        # Step 5: Build Flashing Command
        flash_mode = config.get("flash_mode", "dio")
        flash_freq = config.get("flash_freq", "40m")
        flash_addr = config.get("default_address", "0x0")

        # Chip-specific address handling: ESP8266 starts at 0x0; ESP32 raw binaries start at 0x1000 or 0x0
        # If binary is complete merged image, 0x0 is standard
        cmd = self.get_esptool_command() + [
            "--port", port,
            "--baud", str(baudrate),
            "--chip", "auto",
            "--before", "default_reset",
            "--after", "hard_reset",
            "write_flash",
            "--flash_mode", flash_mode,
            "--flash_freq", flash_freq,
            "--flash_size", "detect"
        ]

        if erase_all:
            cmd.append("--erase-all")
            init_msg = "Membersihkan flash chip & menyiapkan flashing..."
            init_stage = STATUS_ERASING
        else:
            init_msg = "Menyiapkan penulisan flash biner..."
            init_stage = STATUS_FLASHING

        if verify_flash:
            cmd.append("--verify")

        with FirmwareService.get_ephemeral_binary(fw_path) as active_bin_path:
            cmd.extend([flash_addr, str(active_bin_path.resolve())])

            emit_log(f"Executing: {' '.join(cmd)}")
            emit_progress(35, init_stage, init_msg)

            # Step 6: Execute Process & Parse Real-Time Output
            full_output = []
            verified_ok = False
            progress_val = 35

            try:
                with self._lock:
                    self._current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )

                # Stream output
                for line in self._current_process.stdout:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    full_output.append(line_str)
                    emit_log(f"[esptool] {line_str}")

                    # Real-time Erasing Detection
                    if "Erasing flash" in line_str:
                        emit_progress(35, STATUS_ERASING, "Membersihkan seluruh memori flash (Chip Erase)...")
                    elif "Chip erase completed" in line_str:
                        emit_progress(45, STATUS_FLASHING, "Erase Chip selesai. Mulai penulisan biner...")

                    # Progress parsing: e.g. "Writing at 0x00000000... (25 %)"
                    pct_match = re.search(r"\((\d+)\s*%\)", line_str)
                    if pct_match:
                        esp_pct = int(pct_match.group(1))
                        base_offset = 45 if erase_all else 35
                        scale = 0.47 if erase_all else 0.55
                        overall_pct = base_offset + int(esp_pct * scale)
                        emit_progress(overall_pct, STATUS_FLASHING, f"Writing Flash: {esp_pct}%")

                    if "Verifying just-written data" in line_str or "Verifying..." in line_str:
                        emit_progress(92, STATUS_VERIFYING, "Verifying Flash Hash...")

                    if "Hash of data verified." in line_str or "Leaving... Staying in bootloader." in line_str:
                        verified_ok = True

                    if self._is_cancelled:
                        break

                self._current_process.wait(timeout=10)
                exit_code = self._current_process.returncode

            except subprocess.TimeoutExpired:
                self._current_process.kill()
                exit_code = -1
                emit_log("ERROR: Process timed out during flashing.")
            except Exception as e:
                exit_code = -2
                emit_log(f"ERROR: Subprocess execution exception: {str(e)}")
            finally:
                with self._lock:
                    self._current_process = None

        record.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
        record.duration_seconds = round(time.monotonic() - start_mono, 2)

        # Step 7: Evaluate Real Results
        if self._is_cancelled:
            emit_log("Flashing CANCELLED by operator.")
            emit_progress(100, STATUS_CANCELLED, "Process Cancelled", is_term=True)
            record.result = STATUS_CANCELLED
            record.error_message = "Flashing was intentionally cancelled by operator. Flash memory may be incomplete."
            record.verification_status = "FAILED"
        elif exit_code == 0:
            if verify_flash and not verified_ok:
                # Process returned 0 but verification phrase missing
                emit_log("WARNING: esptool exited 0 but explicit hash verification phrase was not found.")
                record.verification_status = "UNVERIFIED"
            else:
                record.verification_status = "VERIFIED" if verify_flash else "SKIPPED"

            record.result = STATUS_PASS
            emit_log(f"FLASHING COMPLETED SUCCESSFULLY in {record.duration_seconds}s! Status: PASS")
            emit_progress(100, STATUS_PASS, f"PASS ({record.duration_seconds}s)", is_term=True)
        else:
            emit_log(f"FLASHING FAILED with exit code {exit_code}.")
            emit_progress(100, STATUS_FAIL, f"FAIL (Exit code {exit_code})", is_term=True)
            record.result = STATUS_FAIL
            record.verification_status = "FAILED"
            record.error_message = f"esptool exited with error code {exit_code}.\n" + "\n".join(full_output[-10:])

        # Save to database
        db_manager.insert_record(record)

        # Auto-register to live fleet monitoring roster if flashing was successful
        if record.result == STATUS_PASS and record.mac_address and record.mac_address != "UNKNOWN":
            try:
                from src.services.mqtt_service import mqtt_service
                mqtt_service.auto_register_flashed_device(
                    mac_address=record.mac_address,
                    category=record.product_category,
                    batch_name=record.batch_name
                )
            except Exception as e:
                logger.warning(f"Could not auto-register device into fleet roster: {e}")

        return record

    def _run_simulation(
        self,
        record: ProductionRecord,
        fw_info: FirmwareInfo,
        start_mono: float,
        verify_flash: bool,
        erase_all: bool,
        emit_progress: Callable,
        emit_log: Callable
    ) -> ProductionRecord:
        """Realistic simulated flashing pipeline for offline verification and testing."""
        emit_log("[SIMULATION MODE] Running simulated flashing cycle...")
        sim_chip = "ESP32-C3 (Simulated)" if record.product_category == PRODUCT_PLUG else "ESP32-D0WD Dual Core (Simulated)"
        record.target_chip = sim_chip
        record.mac_address = "30:AE:A4:7F:1B:2C"
        record.operator_notes = (record.operator_notes or "") + " [SIMULATED_TEST]"

        emit_progress(15, STATUS_CONNECTING, f"Connecting to simulated target ({sim_chip})...")
        time.sleep(0.3)
        if self._is_cancelled:
            return self._handle_sim_cancel(record, start_mono, emit_progress, emit_log)

        emit_progress(30, STATUS_CHIP_DETECTED, f"Chip Verified: {sim_chip}")
        emit_log(f"Simulated Chip: {sim_chip} | MAC: 30:AE:A4:7F:1B:2C")
        time.sleep(0.3)

        if erase_all:
            emit_progress(35, STATUS_ERASING, "Membersihkan seluruh memori flash (--erase-all)...")
            emit_log("[esptool-sim] Erasing flash (this may take a while)...")
            time.sleep(0.4)
            if self._is_cancelled:
                return self._handle_sim_cancel(record, start_mono, emit_progress, emit_log)
            emit_log("[esptool-sim] Chip erase completed successfully in 0.4s.")
            emit_progress(45, STATUS_FLASHING, "Erase Chip selesai. Mulai penulisan biner...")

        base_offset = 45 if erase_all else 35
        scale = 0.47 if erase_all else 0.55

        for pct in [10, 25, 45, 65, 85, 100]:
            if self._is_cancelled:
                return self._handle_sim_cancel(record, start_mono, emit_progress, emit_log)
            overall = base_offset + int(pct * scale)
            emit_progress(overall, STATUS_FLASHING, f"Writing Flash: {pct}%")
            emit_log(f"[esptool-sim] Writing at 0x{(pct * 1024):08X}... ({pct} %)")
            time.sleep(0.15)

        emit_progress(95, STATUS_VERIFYING, "Verifying Flash Hash...")
        emit_log("[esptool-sim] Hash of data verified.")
        time.sleep(0.2)

        record.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
        record.duration_seconds = round(time.monotonic() - start_mono, 2)
        record.result = STATUS_PASS
        record.verification_status = "VERIFIED" if verify_flash else "SKIPPED"
        emit_progress(100, STATUS_PASS, f"PASS ({record.duration_seconds}s)", is_term=True)
        emit_log(f"SIMULATED FLASH PASS in {record.duration_seconds}s!")

        db_manager.insert_record(record)
        return record

    def _handle_sim_cancel(self, record: ProductionRecord, start_mono: float, emit_progress: Callable, emit_log: Callable) -> ProductionRecord:
        record.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
        record.duration_seconds = round(time.monotonic() - start_mono, 2)
        record.result = STATUS_CANCELLED
        record.verification_status = "FAILED"
        record.error_message = "Simulated flashing cancelled by operator."
        emit_progress(100, STATUS_CANCELLED, "Cancelled", is_term=True)
        emit_log("Simulated flashing cancelled.")
        db_manager.insert_record(record)
        return record

# Global service singleton
flasher_service = FlasherService()
