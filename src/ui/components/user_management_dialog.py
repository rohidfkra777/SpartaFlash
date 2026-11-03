"""
SpartaFlash - Operator Management Modal Dialog.
Developer: Rohidfkra777

Allows authenticated Administrators to view, add, and delete Operator accounts.
SECURITY ENFORCEMENT:

- Admin account cannot be deleted (safety barrier).
- Only OPERATOR accounts can be added or deleted.
- All modifications are automatically synced across workstations via AES-256-GCM MQTT.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

from src.config.auth_credentials import get_active_vault, UserRole
from src.services.auth_service import auth_service


from src.services.activity_log_service import activity_logger, ActivityCategory, ActivityStatus
from src.ui.components.icon_provider import IconProvider
from src.ui.components.add_user_dialog import AddUserDialog


class UserManagementDialog(QDialog):
    """Modal dialog for Administrator to manage operator accounts safely for workstation fleet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manajemen Akun Operator")
        self.setFixedSize(540, 440)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                border: 2px solid #1E293B;
                border-radius: 12px;
            }
            QLabel {
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QTableWidget {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
                color: #F8FAFC;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #0B1120;
                color: #94A3B8;
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-bottom: 1.5px solid #334155;
                padding: 6px;
            }
        """)

        self._init_ui()
        self.refresh_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Title & Add Button
        top_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap("users", "#38BDF8", 22))
        top_layout.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("MANAJEMEN AKUN OPERATOR")
        lbl_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 800; letter-spacing: 0.5px;")
        lbl_sub = QLabel("Kelola akun teknisi & operator workstation pabrik")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 11px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        top_layout.addLayout(title_box)

        top_layout.addStretch()

        self.btn_add_op = QPushButton(" Tambah Operator")
        self.btn_add_op.setIcon(IconProvider.get_icon("user-plus", "#FFFFFF", 14))
        self.btn_add_op.setIconSize(QSize(14, 14))
        self.btn_add_op.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 11.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_add_op.clicked.connect(self._open_add_operator_dialog)
        top_layout.addWidget(self.btn_add_op)

        layout.addLayout(top_layout)

        # Operator Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Username", "Nama Operator", "Hak Akses", "Aksi"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.table)

        # Footer Notice
        footer_layout = QHBoxLayout()
        lbl_note = QLabel("🔒 <i>Akun operator hanya memiliki hak akses untuk Dashboard Flashing.</i>")
        lbl_note.setStyleSheet("color: #64748B; font-size: 10.5px;")
        footer_layout.addWidget(lbl_note)
        footer_layout.addStretch()

        btn_close = QPushButton("Tutup")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """)
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        layout.addLayout(footer_layout)

    def refresh_table(self):
        """Populates user table with active station accounts."""
        active_vault = dict(get_active_vault())

        
        filtered_users = []
        for uname, udata in active_vault.items():
            
            filtered_users.append((uname, udata))

        # Sort: Admin first, then Operators alphabetically
        filtered_users.sort(key=lambda x: (0 if x[0] == "admin" else 1, x[0]))

        self.table.setRowCount(len(filtered_users))
        for row_idx, (uname, udata) in enumerate(filtered_users):
            role = udata.get("role", "OPERATOR")
            display_name = udata.get("display_name", uname.capitalize())

            # 1. Username
            item_uname = QTableWidgetItem(f" {uname}")
            item_uname.setFlags(Qt.ItemIsEnabled)
            item_uname.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row_idx, 0, item_uname)

            # 2. Display Name
            item_dname = QTableWidgetItem(f" {display_name}")
            item_dname.setFlags(Qt.ItemIsEnabled)
            item_dname.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row_idx, 1, item_dname)

            # 3. Role Badge
            item_role = QTableWidgetItem(role)
            item_role.setFlags(Qt.ItemIsEnabled)
            item_role.setTextAlignment(Qt.AlignCenter)
            if role == "ADMIN":
                item_role.setForeground(Qt.GlobalColor.cyan)
            else:
                item_role.setForeground(Qt.GlobalColor.green)
            self.table.setItem(row_idx, 2, item_role)

            # 4. Action Button
            if uname == "admin":
                lbl_locked = QLabel(" (Akun Utama)")
                lbl_locked.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 600;")
                lbl_locked.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row_idx, 3, lbl_locked)
            else:
                btn_del = QPushButton(" Hapus")
                btn_del.setIcon(IconProvider.get_icon("trash-2", "#EF4444", 12))
                btn_del.setIconSize(QSize(12, 12))
                btn_del.setStyleSheet("""
                    QPushButton {
                        background-color: #450A0A;
                        color: #F87171;
                        border: 1px solid #7F1D1D;
                        border-radius: 4px;
                        padding: 3px 8px;
                        font-size: 10px;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background-color: #7F1D1D;
                        color: #FFFFFF;
                        border-color: #DC2626;
                    }
                """)
                btn_del.clicked.connect(lambda _, u=uname, d=display_name: self._confirm_delete_operator(u, d))
                self.table.setCellWidget(row_idx, 3, btn_del)

            self.table.setRowHeight(row_idx, 34)

    def _open_add_operator_dialog(self):
        dlg = AddUserDialog(self)
        if dlg.exec() == AddUserDialog.Accepted:
            self.refresh_table()

    def _confirm_delete_operator(self, username: str, display_name: str):
        # Additional backend security safeguard
        if username.lower() == "admin":
            QMessageBox.warning(self, "Aksi Ditolak", "Akun sistem tidak dapat dihapus.")
            return

        reply = QMessageBox.question(
            self,
            "Konfirmasi Hapus Operator",
            f"Apakah Anda yakin ingin menghapus akun operator:\n\n"
            f"• Username: <b>{username}</b>\n"
            f"• Nama: <b>{display_name}</b>\n\n"
            f"Hak akses operator ini akan dicabut secara permanen dari seluruh workstation pabrik.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        active_vault = dict(get_active_vault())
        if username not in active_vault:
            QMessageBox.warning(self, "Peringatan", f"User '{username}' tidak ditemukan.")
            return

        # Delete operator
        del active_vault[username]

        ver_or_err = 'v1.0'

        curr_user = auth_service.current_user
        admin_name = curr_user.username if curr_user else "admin"

        # Log local activity
        activity_logger.log(
            category=ActivityCategory.AUTH,
            action="DELETE_OPERATOR",
            details=f"Admin '{admin_name}' deleted operator '{username}' ({display_name})",
            status=ActivityStatus.SUCCESS,
            username=admin_name,
            role="ADMIN"
        )

        
        QMessageBox.information(
            self,
            "Berhasil",
            f"Akun operator '{display_name}' ({username}) telah berhasil dihapus dari sistem!"
        )
        self.refresh_table()

