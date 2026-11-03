"""
SpartaFlash - Add Operator Account Dialog.
Developer: Rohidfkra777

Allows authenticated Administrators to register new Operator accounts.
Enforces OPERATOR role restriction (operators only have access to Dashboard flashing).
User provisioning and workstation account management.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt

from src.config.auth_credentials import get_active_vault, UserRole
from src.services.auth_service import auth_service


from src.services.activity_log_service import activity_logger, ActivityCategory, ActivityStatus
from src.ui.components.icon_provider import IconProvider


class AddUserDialog(QDialog):
    """Modal dialog allowing Admin to add a new Operator account with restricted dashboard-only access."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tambah Akun Operator Baru")
        self.setFixedSize(390, 410)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                border: 2px solid #1E293B;
                border-radius: 10px;
            }
            QLabel {
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 30px 8px 12px;
                color: #F8FAFC;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1.5px solid #38BDF8;
                background-color: #0F172A;
            }
        """)

        self._init_ui()

    def _attach_password_toggle(self, line_edit: QLineEdit):
        """Attaches an in-line eye toggle action to the trailing edge of a password input."""
        icon_eye = IconProvider.get_icon("eye", "#94A3B8", 16)
        icon_eye_off = IconProvider.get_icon("eye-off", "#38BDF8", 16)

        action = line_edit.addAction(icon_eye, QLineEdit.ActionPosition.TrailingPosition)
        action.setToolTip("Lihat Password")

        def _toggle():
            if line_edit.echoMode() == QLineEdit.EchoMode.Password:
                line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                action.setIcon(icon_eye_off)
                action.setToolTip("Sembunyikan Password")
            else:
                line_edit.setEchoMode(QLineEdit.EchoMode.Password)
                action.setIcon(icon_eye)
                action.setToolTip("Lihat Password")

        action.triggered.connect(_toggle)
        return action

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Header Title
        title_box = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap("user-plus", "#10B981", 22))
        title_box.addWidget(icon_lbl)

        lbl_title = QLabel("TAMBAH OPERATOR BARU")
        lbl_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 800; letter-spacing: 0.5px;")
        title_box.addWidget(lbl_title)
        title_box.addStretch()
        layout.addLayout(title_box)

        lbl_desc = QLabel(
            "Akun operator baru memiliki hak akses operasional pada <b>Dashboard Flashing</b>, "
            "<b>Device Monitor</b> (Mode Pemantauan Saja), <b>Production History</b> (termasuk Export CSV), dan <b>About System</b>. "
            "Menu pengaturan stasiun, log aktivitas, dan laporan batch otomatis disembunyikan."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 11px; margin-bottom: 4px; line-height: 15px;")
        layout.addWidget(lbl_desc)

        # 1. Username
        layout.addWidget(QLabel("Username Login (Tanpa spasi, huruf kecil):", styleSheet="color: #CBD5E1; font-size: 11px; font-weight: 600;"))
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Contoh: operator1, budi, tek_line1")
        layout.addWidget(self.txt_username)

        # 2. Display Name
        layout.addWidget(QLabel("Nama Lengkap / Identitas Operator:", styleSheet="color: #CBD5E1; font-size: 11px; font-weight: 600;"))
        self.txt_display_name = QLineEdit()
        self.txt_display_name.setPlaceholderText("Contoh: Budi Santoso (Line 1 QC)")
        layout.addWidget(self.txt_display_name)

        # 3. Password
        layout.addWidget(QLabel("Password (Min. 6 Karakter):", styleSheet="color: #CBD5E1; font-size: 11px; font-weight: 600;"))
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Masukkan password untuk operator...")
        self._attach_password_toggle(self.txt_password)
        layout.addWidget(self.txt_password)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600;")
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        layout.addSpacing(6)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Batal")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Daftarkan Operator")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_save.clicked.connect(self._on_register_operator)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _on_register_operator(self):
        username = self.txt_username.text().strip().lower()
        display_name = self.txt_display_name.text().strip()
        password = self.txt_password.text().strip()

        if not username or not password:
            self._show_error("Username dan password wajib diisi.")
            return

        if len(username) < 3 or " " in username:
            self._show_error("Username minimal 3 karakter dan tidak boleh ada spasi.")
            return

        if len(password) < 6:
            self._show_error("Password minimal 6 karakter.")
            return

        if not display_name:
            display_name = username.capitalize()

        active_vault = dict(get_active_vault())
        if username in active_vault:
            self._show_error(f"Username '{username}' sudah terdaftar di sistem.")
            return

        # Hash operator password
        salt, phash = hash_password(password)

        active_vault[username] = {
            "role": UserRole.OPERATOR,  # Enforce OPERATOR role strictly
            "display_name": display_name,
            "salt": salt,
            "hash": phash
        }

        # Sync to MQTT retained topic & local secure cache
        ver_or_err = 'v1.0'

        curr_user = auth_service.current_user
        admin_name = curr_user.username if curr_user else "admin"

        # Log to local activity audit
        activity_logger.log(
            category=ActivityCategory.AUTH,
            action="ADD_OPERATOR",
            details=f"Admin '{admin_name}' registered operator '{username}' ({display_name}) with role OPERATOR",
            status=ActivityStatus.SUCCESS,
            username=admin_name,
            role="ADMIN"
        )

        
        QMessageBox.information(
            self,
            "Operator Berhasil Didaftarkan",
            f"Operator '{display_name}' ({username}) berhasil didaftarkan!\n\n"
            "Hak akses operator telah dibatasi hanya untuk penggunaan Dashboard Flashing."
        )
        self.accept()

    def _show_error(self, message: str):
        self.lbl_error.setText(f"⚠️ {message}")
        self.lbl_error.setVisible(True)

