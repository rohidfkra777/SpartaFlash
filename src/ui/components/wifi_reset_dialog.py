"""
SpartaFlash - Wi-Fi Reset & Re-provisioning Safety Modal Dialog.
Developer: Rohidfkra777

Provides operators and facility engineers with a secure, fail-safe dialog to:
1. Reset device Wi-Fi into standalone Hotspot AP Mode (192.168.4.1) for on-site phone setup.
2. Direct remote migration to a new Store SSID & Password (Zero-Touch handover).
3. Optional concurrent total kWh zeroing and LittleFS offline buffer formatting.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QRadioButton, QCheckBox,
    QFrame, QButtonGroup, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.ui.components.icon_provider import IconProvider


class WifiResetDialog(QDialog):
    """
    Industrial safety dialog for resetting and re-provisioning device Wi-Fi credentials.
    Supports standalone AP hotspot fallback or direct new SSID/Password input.
    """

    def __init__(self, device_name: str, mac_key: str, parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self.mac_key = mac_key

        self.setWindowTitle("Konfirmasi Reset & Pergantian Wi-Fi Perangkat")
        self.resize(540, 520)
        self.setMinimumSize(480, 460)

        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
            }
            QLabel {
                color: #F8FAFC;
            }
            QFrame.card {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QRadioButton {
                color: #F8FAFC;
                font-size: 12px;
                font-weight: 700;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox {
                color: #CBD5E1;
                font-size: 11px;
                font-weight: 600;
                spacing: 8px;
            }
            QLineEdit {
                background-color: #0B1120;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 12px;
                color: #F8FAFC;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #38BDF8;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Danger Warning Banner
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background-color: #450A0A;
                border: 1px solid #EF4444;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(10, 8, 10, 8)
        b_layout.setSpacing(4)

        lbl_b_title = QLabel("⚠️ PERINGATAN KESELAMATAN: RESET JARINGAN WI-FI")
        lbl_b_title.setStyleSheet("color: #EF4444; font-weight: 800; font-size: 12px;")
        
        lbl_b_desc = QLabel(
            "Perintah ini akan memutuskan perangkat dari koneksi Wi-Fi saat ini. "
            "Pastikan parameter jaringan baru sudah sesuai sebelum dieksekusi."
        )
        lbl_b_desc.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        lbl_b_desc.setWordWrap(True)

        b_layout.addWidget(lbl_b_title)
        b_layout.addWidget(lbl_b_desc)
        layout.addWidget(banner)

        # 2. Target Device Info Box
        info_frame = QFrame()
        info_frame.setProperty("class", "card")
        info_frame.setStyleSheet("""
            QFrame.card {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 6, 8, 6)

        lbl_target_title = QLabel("Target Perangkat:")
        lbl_target_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        
        lbl_target_val = QLabel(f"{self.device_name}  (MAC Key: {self.mac_key})")
        lbl_target_val.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 800;")

        info_layout.addWidget(lbl_target_title)
        info_layout.addWidget(lbl_target_val)
        info_layout.addStretch()
        layout.addWidget(info_frame)

        # 3. Method Selection Container
        method_frame = QFrame()
        method_frame.setProperty("class", "card")
        method_frame.setStyleSheet("""
            QFrame.card {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        method_layout = QVBoxLayout(method_frame)
        method_layout.setContentsMargins(10, 10, 10, 10)
        method_layout.setSpacing(10)

        lbl_method_title = QLabel("Pilih Metode Pergantian Jaringan:")
        lbl_method_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        method_layout.addWidget(lbl_method_title)

        self.btn_group = QButtonGroup(self)

        # Method 1: Standalone AP Hotspot Mode
        self.rad_hotspot = QRadioButton("Mode 1: Reset ke Hotspot Mandiri (Access Point 192.168.4.1)")
        self.btn_group.addButton(self.rad_hotspot, 1)
        method_layout.addWidget(self.rad_hotspot)

        lbl_hotspot_desc = QLabel(
            "   └─ Menghapus Wi-Fi lama. Perangkat me-reboot dan memancarkan Hotspot Wi-Fi mandiri "
            "agar teknisi di toko bisa menyambungkannya ke SSID baru lewat HP."
        )
        lbl_hotspot_desc.setStyleSheet("color: #94A3B8; font-size: 10px;")
        lbl_hotspot_desc.setWordWrap(True)
        method_layout.addWidget(lbl_hotspot_desc)

        # Method 2: Direct Switch to New SSID
        self.rad_direct = QRadioButton("Mode 2: Langsung Alihkan ke SSID Toko Baru (Direct Handover)")
        self.btn_group.addButton(self.rad_direct, 2)
        method_layout.addWidget(self.rad_direct)

        lbl_direct_desc = QLabel(
            "   └─ Perangkat langsung beralih ke SSID & password baru ini dan me-restart secara otomatis."
        )
        lbl_direct_desc.setStyleSheet("color: #94A3B8; font-size: 10px;")
        lbl_direct_desc.setWordWrap(True)
        method_layout.addWidget(lbl_direct_desc)

        # Container for Direct SSID & Password Inputs
        self.input_container = QFrame()
        self.input_container.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        in_layout = QVBoxLayout(self.input_container)
        in_layout.setContentsMargins(8, 8, 8, 8)
        in_layout.setSpacing(8)

        # SSID input
        lbl_ssid = QLabel("Nama Wi-Fi (SSID) Baru:")
        lbl_ssid.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 600;")
        in_layout.addWidget(lbl_ssid)

        self.txt_ssid = QLineEdit()
        self.txt_ssid.setPlaceholderText("Contoh: Store_T105_IoT atau MyRouter_2.4G")
        in_layout.addWidget(self.txt_ssid)

        # Password input with show/hide toggle
        lbl_pass = QLabel("Password Wi-Fi Baru:")
        lbl_pass.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 600;")
        in_layout.addWidget(lbl_pass)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(6)

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Masukkan password Wi-Fi baru...")
        pass_row.addWidget(self.txt_password, stretch=1)

        self.btn_toggle_pass = QPushButton("Lihat")
        self.btn_toggle_pass.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """)
        self.btn_toggle_pass.clicked.connect(self._toggle_password_visibility)
        pass_row.addWidget(self.btn_toggle_pass)

        in_layout.addLayout(pass_row)
        method_layout.addWidget(self.input_container)

        layout.addWidget(method_frame)

        # 4. Additional Clean-up Checkboxes (kWh and Buffer)
        opt_frame = QFrame()
        opt_frame.setProperty("class", "card")
        opt_frame.setStyleSheet("""
            QFrame.card {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 12px;
            }
        """)
        opt_layout = QVBoxLayout(opt_frame)
        opt_layout.setContentsMargins(8, 8, 8, 8)
        opt_layout.setSpacing(6)

        lbl_opt_title = QLabel("Opsi Tambahan Pembersihan (Opsional):")
        lbl_opt_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        opt_layout.addWidget(lbl_opt_title)

        self.chk_reset_kwh = QCheckBox("Nol-kan Total kWh (Reset Akumulasi Energi ke 0.00 kWh)")
        self.chk_reset_kwh.setToolTip("Centang jika alat akan dipasang ke toko atau panel baru agar meteran mulai dari nol.")
        self.chk_reset_kwh.setChecked(True)
        opt_layout.addWidget(self.chk_reset_kwh)

        self.chk_clear_buffer = QCheckBox("Bersihkan Buffer Offline LittleFS (Hapus Riwayat Toko Lama)")
        self.chk_clear_buffer.setToolTip("Format memori buffer flash LittleFS agar riwayat telemetri toko lama tidak tercampur.")
        self.chk_clear_buffer.setChecked(True)
        opt_layout.addWidget(self.chk_clear_buffer)

        layout.addWidget(opt_frame)

        # 5. Fail-Safe Advice Note
        lbl_failsafe = QLabel(
            "🛡️ <b>Jaring Pengaman (Fail-Safe):</b> Jika salah ketik password di Mode 2, perangkat "
            "otomatis membuka Hotspot AP darurat setelah ~3 menit gagal sambung (Anti-Macet)."
        )
        lbl_failsafe.setStyleSheet("color: #38BDF8; font-size: 10px;")
        lbl_failsafe.setWordWrap(True)
        layout.addWidget(lbl_failsafe)

        layout.addStretch()

        # 6. Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_cancel = QPushButton("Batal")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        self.btn_execute = QPushButton("⚠️ Eksekusi Reset Wi-Fi")
        self.btn_execute.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: #FFFFFF;
                border: 1px solid #DC2626;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        self.btn_execute.clicked.connect(self._on_execute_clicked)
        btn_box.addWidget(self.btn_execute)

        layout.addLayout(btn_box)

        # Default selection: Direct Mode if available, or Hotspot
        self.rad_direct.setChecked(True)
        self.rad_hotspot.toggled.connect(self._on_method_toggled)
        self.rad_direct.toggled.connect(self._on_method_toggled)
        self._on_method_toggled()

    def _on_method_toggled(self):
        """Shows/hides the direct SSID & Password input fields based on chosen method."""
        is_direct = self.rad_direct.isChecked()
        self.input_container.setVisible(is_direct)

    def _toggle_password_visibility(self):
        if self.txt_password.echoMode() == QLineEdit.Password:
            self.txt_password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_pass.setText("Tutup")
        else:
            self.txt_password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_pass.setText("Lihat")

    def _on_execute_clicked(self):
        """Validates inputs and confirms execution."""
        if self.rad_direct.isChecked():
            ssid = self.txt_ssid.text().strip()
            if not ssid:
                QMessageBox.warning(
                    self, "SSID Kosong",
                    "Silakan masukkan Nama Wi-Fi (SSID) baru untuk Mode 2, atau pilih Mode 1 (Hotspot AP)."
                )
                self.txt_ssid.setFocus()
                return

        self.accept()

    def get_execution_plan(self) -> Dict[str, Any]:
        """Returns structured dictionary of actions to execute via MQTT."""
        is_direct = self.rad_direct.isChecked()
        return {
            "method": "DIRECT" if is_direct else "HOTSPOT",
            "ssid": self.txt_ssid.text().strip() if is_direct else "",
            "password": self.txt_password.text().strip() if is_direct else "",
            "reset_kwh": self.chk_reset_kwh.isChecked(),
            "clear_buffer": self.chk_clear_buffer.isChecked()
        }
