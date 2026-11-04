"""
SpartaFlash - Sleek Industrial Station Login Modal Dialog.
Developer: Rohidfkra777

Enforces silent background internet barrier and dynamic remote credential synchronization.

"""

import sys
import ctypes
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QApplication, QStackedLayout, QWidget
)
from src.ui.components.cute_offline_overlay import CuteOfflineOverlay
from PySide6.QtCore import Qt, QTimer, QEvent, QObject
from PySide6.QtGui import QIcon, QPixmap

from src.config.constants import APP_NAME, APP_VERSION, APP_ICON_PATH
from src.services.auth_service import auth_service


from src.ui.components.icon_provider import IconProvider


class CapsLockFilter(QObject):
    """Event filter to detect Caps Lock state on keyboard entry."""
    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self.callback = callback

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.KeyPress, QEvent.KeyRelease, QEvent.FocusIn):
            self.callback()
        elif event.type() == QEvent.FocusOut:
            self.callback(hide=True)
        return super().eventFilter(obj, event)


class LoginDialog(QDialog):
    """
    Industrial Dark modal dialog that gates workstation access.
    Operates a silent internet verification barrier without exposing gateway status in UI.
    """
    def __init__(self, parent=None, is_switch_user: bool = False):
        super().__init__(parent)
        self.is_switch_user = is_switch_user
        self.setWindowTitle(f"Station Login - {APP_NAME}")
        self.setFixedSize(380, 400)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0B1120;
                border: 1px solid #1E293B;
                border-radius: 12px;
            }
            QLabel {
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
        """)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._update_lockout_timer)

        self._init_ui()

        

    def _init_ui(self):
        self.root_stack = QStackedLayout(self)
        self.root_stack.setContentsMargins(0, 0, 0, 0)

        # Page 0: Login Form Page
        self.page_login = QWidget()
        layout = QVBoxLayout(self.page_login)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(0)

        # 1. Header Banner
        header_box = QVBoxLayout()
        header_box.setAlignment(Qt.AlignCenter)
        header_box.setSpacing(2)

        if APP_ICON_PATH.exists():
            lbl_icon = QLabel()
            lbl_icon.setAlignment(Qt.AlignCenter)
            lbl_icon.setPixmap(QPixmap(str(APP_ICON_PATH)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            header_box.addWidget(lbl_icon)

        lbl_title = QLabel()
        lbl_title.setTextFormat(Qt.RichText)
        lbl_title.setText("<span style='color: #38BDF8;'>SPARTA</span><span style='color: #EF4444; font-style: italic;'>FLASH</span>")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 17px; font-weight: 900; letter-spacing: 1px; margin-top: 4px; font-family: 'Segoe UI', -apple-system, sans-serif;")
        header_box.addWidget(lbl_title)

        lbl_sub = QLabel("STATION OPERATOR ACCESS CONTROL")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("color: #64748B; font-size: 9.5px; font-weight: 700; letter-spacing: 0.8px;")
        header_box.addWidget(lbl_sub)

        layout.addLayout(header_box)
        layout.addSpacing(28)

        # 2. Form Inputs
        lbl_u = QLabel("USERNAME")
        lbl_u.setFixedHeight(15)
        lbl_u.setStyleSheet("color: #94A3B8; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")
        layout.addWidget(lbl_u)
        layout.addSpacing(6)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("ID Operator / Username")
        self.txt_username.setFixedHeight(38)
        self.txt_username.setStyleSheet("""
            QLineEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1.5px solid #1E293B;
                border-radius: 6px;
                padding-left: 28px;
                padding-right: 12px;
                font-size: 12.5px;
            }
            QLineEdit:focus {
                border-color: #38BDF8;
                background-color: #131E33;
            }
        """)
        self.txt_username.addAction(IconProvider.get_icon("user", "#64748B", 14), QLineEdit.ActionPosition.LeadingPosition)
        layout.addWidget(self.txt_username)

        layout.addSpacing(18)

        lbl_p = QLabel("PASSWORD")
        lbl_p.setFixedHeight(15)
        lbl_p.setStyleSheet("color: #94A3B8; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")
        layout.addWidget(lbl_p)
        layout.addSpacing(6)

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Kata sandi stasiun")
        self.txt_password.setFixedHeight(38)
        self.txt_password.setStyleSheet("""
            QLineEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1.5px solid #1E293B;
                border-radius: 6px;
                padding-left: 28px;
                padding-right: 32px;
                font-size: 12.5px;
            }
            QLineEdit:focus {
                border-color: #38BDF8;
                background-color: #131E33;
            }
        """)
        self.txt_password.addAction(IconProvider.get_icon("key", "#64748B", 14), QLineEdit.ActionPosition.LeadingPosition)
        self._attach_password_toggle(self.txt_password)
        self.txt_password.returnPressed.connect(self._handle_login)
        self.txt_username.returnPressed.connect(lambda: self.txt_password.setFocus())
        layout.addWidget(self.txt_password)

        # Caps lock warning banner
        self.lbl_caps_warning = QLabel("⚠️ Caps Lock aktif — periksa huruf besar/kecil kata sandi")
        self.lbl_caps_warning.setStyleSheet("""
            background-color: rgba(245, 158, 11, 0.12);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.35);
            border-radius: 5px;
            padding: 3px 6px;
            font-size: 10.5px;
            font-weight: 600;
            margin-top: 4px;
        """)
        self.lbl_caps_warning.setVisible(False)
        layout.addWidget(self.lbl_caps_warning)

        # Install Caps Lock detection filter on password field
        self._caps_filter = CapsLockFilter(self._update_caps_warning, self.txt_password)
        self.txt_password.installEventFilter(self._caps_filter)

        # Error / Status Banner
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFixedHeight(18)
        self.lbl_status.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600; margin-top: 4px;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # 3. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        cancel_text = "Cancel" if self.is_switch_user else "Exit App"
        self.btn_cancel = QPushButton(cancel_text)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0px 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_login = QPushButton(" Login Station")
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setFixedHeight(38)
        self.btn_login.setIcon(IconProvider.get_icon("shield", "#FFFFFF", 14))
        self.btn_login.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1);
                color: #FFFFFF;
                border: 1px solid #38BDF8;
                border-radius: 6px;
                padding: 0px 20px;
                font-weight: 700;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #0284C7);
            }
            QPushButton:disabled {
                background-color: #1E293B;
                color: #475569;
                border-color: #334155;
            }
        """)
        self.btn_login.clicked.connect(self._handle_login)
        btn_layout.addWidget(self.btn_login, stretch=1)

        layout.addLayout(btn_layout)

        self.root_stack.addWidget(self.page_login)

        # Page 1: Cute Offline 504 Screen
        self.page_offline = CuteOfflineOverlay(
            on_retry_callback=self._on_offline_retry,
            on_back_callback=self._on_offline_back,
            parent=self
        )
        self.root_stack.addWidget(self.page_offline)

        # Focus username initially if unlocked
        self.txt_username.setFocus()
        self._check_lockout()

    def show_offline_overlay(self):
        self.page_offline.reset_state()
        self.root_stack.setCurrentIndex(1)

    def hide_offline_overlay(self):
        self.root_stack.setCurrentIndex(0)
        self.txt_username.setFocus()

    def _on_offline_retry(self) -> bool:
        return True

    def _on_offline_back(self):
        self.hide_offline_overlay()

    def _on_connectivity_changed(self, is_online: bool):
        pass

    def _attach_password_toggle(self, line_edit: QLineEdit):
        icon_eye = IconProvider.get_icon("eye", "#64748B", 15)
        icon_eye_off = IconProvider.get_icon("eye-off", "#38BDF8", 15)

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

    def _update_caps_warning(self, hide: bool = False):
        if hide:
            self.lbl_caps_warning.setVisible(False)
            return
        if sys.platform == "win32":
            try:
                caps_on = bool(ctypes.windll.user32.GetKeyState(0x14) & 1)
                self.lbl_caps_warning.setVisible(caps_on)
            except Exception:
                self.lbl_caps_warning.setVisible(False)
        else:
            self.lbl_caps_warning.setVisible(False)

    def _check_lockout(self):
        remaining = auth_service.get_lockout_seconds_remaining()
        if remaining > 0:
            self._set_locked_state(remaining)
        else:
            self._set_unlocked_state()

    def _set_locked_state(self, seconds: int):
        self.btn_login.setEnabled(False)
        self.txt_username.setEnabled(False)
        self.txt_password.setEnabled(False)
        self.lbl_status.setText(f"Station locked! Try again in {seconds}s.")
        self.lbl_status.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 800;")
        if not self._countdown_timer.isActive():
            self._countdown_timer.start()

    def _set_unlocked_state(self):
        self._countdown_timer.stop()
        self.btn_login.setEnabled(True)
        self.txt_username.setEnabled(True)
        self.txt_password.setEnabled(True)
        if not self.lbl_status.text().startswith("Too many") and not self.lbl_status.text().startswith("Invalid"):
            self.lbl_status.setText("")

    def _update_lockout_timer(self):
        remaining = auth_service.get_lockout_seconds_remaining()
        if remaining > 0:
            self.lbl_status.setText(f"Station locked! Try again in {remaining}s.")
        else:
            self._set_unlocked_state()

    def _handle_login(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text().strip()

        if not username or not password:
            self.lbl_status.setText("Please enter both username and password.")
            self.lbl_status.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: 700;")
            return

        success, message, user = auth_service.login(username, password)
        if success and user:
            self.accept()
        else:
            self.lbl_status.setText(message)
            self.lbl_status.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 700;")
            self.txt_password.clear()
            self._check_lockout()

    def closeEvent(self, event):
        super().closeEvent(event)

    def reject(self):
        super().reject()
