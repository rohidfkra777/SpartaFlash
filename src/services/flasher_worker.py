"""
SpartaFlash - Dedicated Flashing Background Worker Thread.
Developer: Rohidfkra777
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import QThread, Signal
from src.services.flasher_service import flasher_service, FlashProgress
from src.database.models import ProductionRecord

class FlasherWorker(QThread):
    """Background worker thread to execute flashing without blocking GUI."""

    sig_progress = Signal(int, str, str, bool)  # pct, stage, message, is_terminal
    sig_log = Signal(str)
    sig_finished = Signal(object)  # ProductionRecord
    sig_error = Signal(str)

    def __init__(
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
        parent=None
    ):
        super().__init__(parent)
        self.product_category = product_category
        self.port = port
        self.baudrate = baudrate
        self.custom_firmware_path = custom_firmware_path
        self.batch_name = batch_name
        self.operator_notes = operator_notes
        self.verify_flash = verify_flash
        self.erase_all = erase_all
        self.simulation_mode = simulation_mode

    def run(self):
        try:
            def on_progress(p: FlashProgress):
                self.sig_progress.emit(p.percentage, p.stage, p.message, p.is_terminal)

            def on_log(msg: str):
                self.sig_log.emit(msg)

            record = flasher_service.execute_flash_process(
                product_category=self.product_category,
                port=self.port,
                baudrate=self.baudrate,
                custom_firmware_path=self.custom_firmware_path,
                batch_name=self.batch_name,
                operator_notes=self.operator_notes,
                verify_flash=self.verify_flash,
                erase_all=self.erase_all,
                simulation_mode=self.simulation_mode,
                progress_callback=on_progress,
                log_callback=on_log
            )
            self.sig_finished.emit(record)

        except Exception as e:
            self.sig_error.emit(f"Worker exception: {str(e)}")

    def cancel(self):
        flasher_service.cancel_flashing()
