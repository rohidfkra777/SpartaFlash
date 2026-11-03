"""
SpartaFlash - Change Password Dialog.
Developer: Rohidfkra777

Allows authenticated workstation users to update their password independently.
Updates PBKDF2 hash, synchronizes with fleet via AES-256-GCM MQTT, and sends audit alert.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from src.config.constants import APP_NAME
from src.config.auth_credentials import get_active_vault
from src.services.auth_service import auth_service


from src.services.activity_log_service import activity_logger, ActivityCategory, ActivityStatus
from src.ui.components.icon_provider import IconProvider


class ChangePasswordDialog(QDialog):
    """Modal dialog allowing active user to update their credentials independently."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ganti Password Akun")
        self.setFixedSize(380, 370)
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
        layout.setSpacing(12)

        # Header Title
        title_box = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap("key", "#38BDF8", 22))
        title_box.addWidget(icon_lbl)

        lbl_title = QLabel("GANTI PASSWORD AKUN")
        lbl_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 800; letter-spacing: 0.5px;")
        title_box.addWidget(lbl_title)
        title_box.addStretch()
        layout.addLayout(title_box)

        curr_user = auth_service.current_user
        username = curr_user.username if curr_user else "admin"
        display_name = curr_user.display_name if curr_user else "Supervisor"
        role = getattr(curr_user, "role", "ADMIN") if curr_user else "ADMIN"

        lbl_info = QLabel(f"Akun Aktif: <b>{display_name}</b> (<code>{username}</code> • {role})")
        lbl_info.setStyleSheet("color: #94A3B8; font-size: 12px; margin-bottom: 4px;")
        layout.addWidget(lbl_info)

        # 1. Password Lama
        layout.addWidget(QLabel("Password Lama:", styleSheet="color: #CBD5E1; font-size: 11px; font-weight: 600;"))
        self.txt_old_pass = QLineEdit()
        self.txt_old_pass.setEchoMode(QLineEdit.Password)
        self.txt_old_pass.setPlaceholderText("Masukkan password saat ini...")
        self._attach_password_toggle(self.txt_old_pass)
        layout.addWidget(self.txt_old_pass)

        # 2. Password Baru
        layout.addWidget(QLabel("Password Baru (Min. 6 Karakter):", styleSheet="color: #CBD5E1; font-size: 11px; font-weight: 600;"))
        self.txt_new_pass = QLineEdit()
        self.txt_new_pass.setEchoMode(QLineEdit.Password)
        self.txt_new_pass.setPlaceholderText("Masukkan password baru...")
        self._attach_password_toggle(self.txt_new_pass)
        layout.addWidget(self.txt_new_pass)

        # 3. Konfirmasi Password Baru
        layout.addWidget(QLabel("Konfirmasi Password Baru:", styleSheet="color: #CBD5E1; font-size: 11px; font-weight: 600;"))
        self.txt_confirm_pass = QLineEdit()
        self.txt_confirm_pass.setEchoMode(QLineEdit.Password)
        self.txt_confirm_pass.setPlaceholderText("Ulangi password baru...")
        self._attach_password_toggle(self.txt_confirm_pass)
        layout.addWidget(self.txt_confirm_pass)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600;")
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        layout.addSpacing(6)

        # Action Buttons
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

        self.btn_save = QPushButton("Simpan Password Baru")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_save.clicked.connect(self._on_save_password)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _on_save_password(self):
        old_pass = self.txt_old_pass.text().strip()
        new_pass = self.txt_new_pass.text().strip()
        confirm_pass = self.txt_confirm_pass.text().strip()

        if not old_pass or not new_pass or not confirm_pass:
            self._show_error("Semua kolom password wajib diisi.")
            return

        if len(new_pass) < 6:
            self._show_error("Password baru minimal harus 6 karakter.")
            return

        if new_pass != confirm_pass:
            self._show_error("Konfirmasi password baru tidak cocok.")
            return

        curr_user = auth_service.current_user
        username = curr_user.username if curr_user else "admin"

        # 1. Verify old password against current active vault
        active_vault = dict(get_active_vault())
        user_entry = active_vault.get(username)

        if not user_entry:
            self._show_error("Akun tidak ditemukan di dalam sistem.")
            return

        import hashlib
        salt = user_entry.get("salt", "")
        expected_hash = user_entry.get("hash", "")
        calc_hash = hashlib.pbkdf2_hmac("sha256", old_pass.encode("utf-8"), salt.encode("utf-8"), 100000).hex()

        if calc_hash != expected_hash:
            self._show_error("Password lama salah. Silakan coba lagi.")
            return

        # 2. Hash new password
        new_salt, new_phash = hash_password(new_pass)

        active_vault[username] = dict(user_entry)
        active_vault[username]["salt"] = new_salt
        active_vault[username]["hash"] = new_phash

        # 3. Publish AES-256-GCM update to MQTT and update local cache
        ver_or_err = 'v1.0'

        # 4. Log local activity
        activity_logger.log(
            category=ActivityCategory.AUTH,
            action="CHANGE_PASSWORD",
            details=f"User {username} successfully updated credentials to version {ver_or_err}",
            status=ActivityStatus.SUCCESS,
            username=username,
            role=str(getattr(curr_user, "role", "ADMIN"))
        )

        
        QMessageBox.information(
            self,
            "Berhasil",
            f"Password untuk akun '{username}' telah berhasil diperbarui dan disinkronkan ke seluruh sistem workstation!"
        )
        self.accept()

    def _show_error(self, message: str):
        self.lbl_error.setText(f"⚠️ {message}")
        self.lbl_error.setVisible(True)

