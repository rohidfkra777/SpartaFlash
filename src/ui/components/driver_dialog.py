"""
SpartaFlash - USB Driver Installation Dialog.
Developer: Rohidfkra777
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from src.services.driver_service import DriverService

class DriverDialog(QDialog):
    """Dialog for diagnosing and installing CH340 and CP210x USB serial drivers."""

    sig_drivers_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("USB-TO-UART DRIVER MANAGER")
        self.setFixedWidth(500)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
            }
        """)

        self._init_ui()
        self.refresh_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        lbl_title = QLabel("DIAGNOSTIK & INSTALASI DRIVER USB")
        lbl_title.setStyleSheet("color: #38BDF8; font-size: 16px; font-weight: 800; letter-spacing: 0.5px;")

        lbl_desc = QLabel(
            "Aplikasi membutuhkan driver USB-UART agar dapat berkomunikasi dengan modul ESP8266 & ESP32. "
            "Anda dapat memeriksa status dan menginstal driver resmi (WCH CH340 & Silicon Labs CP210x) secara otomatis."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)

        # Status Cards Frame
        self.frame_status = QFrame()
        self.frame_status.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        self.status_layout = QVBoxLayout(self.frame_status)
        self.status_layout.setSpacing(10)
        layout.addWidget(self.frame_status)

        # Labels for drivers
        self.lbl_ch340 = QLabel("Checking...")
        self.lbl_cp210x = QLabel("Checking...")
        self.lbl_ftdi = QLabel("Checking...")

        for lbl in [self.lbl_ch340, self.lbl_cp210x, self.lbl_ftdi]:
            lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
            self.status_layout.addWidget(lbl)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_install = QPushButton("⚡ Pasang Driver Otomatis (1-Klik)")
        self.btn_install.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #0369A1; }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748B;
            }
        """)
        self.btn_install.clicked.connect(self._run_install)

        btn_close = QPushButton("Tutup")
        btn_close.setProperty("class", "btn-secondary")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #F8FAFC;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_install, stretch=1)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def refresh_status(self):
        data = DriverService.check_installed_drivers()

        def format_status(info):
            color = "#34D399" if info["installed"] else "#F87171"
            icon = "✓" if info["installed"] else "✗"
            return f"{icon} {info['name']}: <span style='color: {color};'>{info['status']}</span>"

        self.lbl_ch340.setText(format_status(data["CH340"]))
        self.lbl_cp210x.setText(format_status(data["CP210x"]))
        self.lbl_ftdi.setText(format_status(data["FTDI"]))

    def _run_install(self):
        self.btn_install.setEnabled(False)
        self.btn_install.setText("Menginstal Driver... (Setujui UAC)")
        QApplication.processEvents()

        res = DriverService.install_bundled_drivers()
        self.refresh_status()
        self.btn_install.setEnabled(True)
        self.btn_install.setText("⚡ Pasang Driver Otomatis (1-Klik)")

        if res["success"]:
            QMessageBox.information(self, "Driver Berhasil Dipasang", res["message"])
            self.sig_drivers_updated.emit()
        else:
            QMessageBox.warning(self, "Hasil Instalasi Driver", res["message"])
