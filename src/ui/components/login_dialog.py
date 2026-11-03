"""
SpartaFlash - Sleek Industrial Station Login Modal Dialog.
Developer: Rohidfkra777

Provides secure station authentication and operator role verification.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QCheckBox, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap

from src.config.constants import APP_NAME, APP_VERSION, APP_ICON_PATH
from src.services.auth_service import auth_service


from src.ui.components.icon_provider import IconProvider

class LoginDialog(QDialog):
    """
    Industrial Dark modal dialog that gates workstation access.
    Modal dialog gating workstation access for authorized station operators.
    """
    def __init__(self, parent=None, is_switch_user: bool = False):
        super().__init__(parent)
        self.is_switch_user = is_switch_user
        self.setWindowTitle(f"Station Login - {APP_NAME}")
        self.setFixedSize(420, 470)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                border: 2px solid #1E293B;
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(14)

        # 1. Header Banner
        header_box = QVBoxLayout()
        header_box.setAlignment(Qt.AlignCenter)
        header_box.setSpacing(4)

        if APP_ICON_PATH.exists():
            lbl_icon = QLabel()
            lbl_icon.setAlignment(Qt.AlignCenter)
            lbl_icon.setPixmap(QPixmap(str(APP_ICON_PATH)).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            header_box.addWidget(lbl_icon)

        lbl_title = QLabel("SPARTAFLASH")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #38BDF8; font-size: 16px; font-weight: 900; letter-spacing: 0.8px;")
        header_box.addWidget(lbl_title)

        lbl_sub = QLabel("STATION OPERATOR ACCESS CONTROL")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        header_box.addWidget(lbl_sub)

        layout.addLayout(header_box)

        # 2. Form Inputs
        lbl_u = QLabel("Username:")
        lbl_u.setStyleSheet("color: #CBD5E1; font-size: 11px; font-weight: 700;")
        layout.addWidget(lbl_u)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Enter username")
        self.txt_username.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                color: #FFFFFF;
                border: 1.5px solid #334155;
                border-radius: 7px;
                padding: 9px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #38BDF8;
                background-color: #16243B;
            }
        """)
        layout.addWidget(self.txt_username)

        lbl_p = QLabel("Password:")
        lbl_p.setStyleSheet("color: #CBD5E1; font-size: 11px; font-weight: 700;")
        layout.addWidget(lbl_p)

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Enter station password")
        self.txt_password.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                color: #FFFFFF;
                border: 1.5px solid #334155;
                border-radius: 7px;
                padding: 9px 30px 9px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #38BDF8;
                background-color: #16243B;
            }
        """)
        self._attach_password_toggle(self.txt_password)
        self.txt_password.returnPressed.connect(self._handle_login)
        self.txt_username.returnPressed.connect(lambda: self.txt_password.setFocus())
        layout.addWidget(self.txt_password)

        # Show password toggle
        self.chk_show_pwd = QCheckBox("Show password")
        self.chk_show_pwd.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.chk_show_pwd.toggled.connect(self._toggle_show_pwd)
        layout.addWidget(self.chk_show_pwd)

        # Error / Status Banner
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 700; min-height: 16px;")
        layout.addWidget(self.lbl_status)

        # 3. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        cancel_text = "Cancel" if self.is_switch_user else "Exit App"
        self.btn_cancel = QPushButton(cancel_text)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 7px;
                padding: 10px 16px;
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
        self.btn_login.setIcon(IconProvider.get_icon("shield", "#FFFFFF", 14))
        self.btn_login.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1);
                color: #FFFFFF;
                border: 1px solid #38BDF8;
                border-radius: 7px;
                padding: 10px 20px;
                font-weight: 800;
                font-size: 13px;
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

        # Focus username initially if unlocked
        self.txt_username.setFocus()
        self._check_lockout()

    def _attach_password_toggle(self, line_edit: QLineEdit):
        icon_eye = IconProvider.get_icon("eye", "#94A3B8", 16)
        icon_eye_off = IconProvider.get_icon("eye-off", "#38BDF8", 16)

        action = line_edit.addAction(icon_eye, QLineEdit.ActionPosition.TrailingPosition)
        action.setToolTip("Lihat Password")

        def _toggle():
            if line_edit.echoMode() == QLineEdit.EchoMode.Password:
                line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                action.setIcon(icon_eye_off)
                action.setToolTip("Sembunyikan Password")
                if hasattr(self, "chk_show_pwd"):
                    self.chk_show_pwd.setChecked(True)
            else:
                line_edit.setEchoMode(QLineEdit.EchoMode.Password)
                action.setIcon(icon_eye)
                action.setToolTip("Lihat Password")
                if hasattr(self, "chk_show_pwd"):
                    self.chk_show_pwd.setChecked(False)

        action.triggered.connect(_toggle)
        return action

    def _toggle_show_pwd(self, checked: bool):
        self.txt_password.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

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
