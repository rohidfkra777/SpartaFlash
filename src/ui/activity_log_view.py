"""
SpartaFlash - User Activity Logs View.
Developer: Rohidfkra777

Displays detailed local audit history of operator actions, station configurations,
flashing transactions, and security events.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QFileDialog, QDialog, QTextEdit
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont

from src.services.activity_log_service import activity_logger, ActivityCategory, ActivityStatus
from src.services.auth_service import auth_service
from src.ui.components.icon_provider import IconProvider


class ActivityLogView(QWidget):
    """Activity and audit log viewer with live updates, filters, and CSV export."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.activities: List[Dict[str, Any]] = []
        self._init_ui()
        self.load_activities()

        # Connect live log signal
        activity_logger.sig_activity_logged.connect(self._on_activity_logged)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Header bar
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("USER ACTIVITY LOGS")
        lbl_title.setStyleSheet("color: #38BDF8; font-size: 20px; font-weight: 800; letter-spacing: 0.5px;")
        lbl_sub = QLabel("Operational audit trail of operator actions and workstation events")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setIcon(IconProvider.get_icon("refresh-cw", "#94A3B8", 15))
        self.btn_refresh.setProperty("class", "btn-secondary")
        self.btn_refresh.clicked.connect(self.load_activities)
        header_layout.addWidget(self.btn_refresh)

        self.btn_export_csv = QPushButton(" Export to CSV")
        self.btn_export_csv.setIcon(IconProvider.get_icon("download", "#FFFFFF", 16))
        self.btn_export_csv.setProperty("class", "btn-primary")
        self.btn_export_csv.clicked.connect(self._export_csv)
        header_layout.addWidget(self.btn_export_csv)

        self.btn_clear = QPushButton(" Clear Log")
        self.btn_clear.setIcon(IconProvider.get_icon("trash-2", "#EF4444", 15))
        self.btn_clear.setProperty("class", "btn-secondary")
        self.btn_clear.setStyleSheet("QPushButton { color: #EF4444; border: 1px solid #7F1D1D; } QPushButton:hover { background-color: #450A0A; }")
        self.btn_clear.clicked.connect(self._clear_logs)
        header_layout.addWidget(self.btn_clear)

        main_layout.addLayout(header_layout)

        # KPI Summary Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.card_total = self._create_kpi_card("TOTAL EVENTS TODAY", "0", "#38BDF8")
        self.card_flashing = self._create_kpi_card("FLASHING OPERATIONS", "0", "#10B981")
        self.card_config = self._create_kpi_card("CONFIGURATION CHANGES", "0", "#F59E0B")
        self.card_last = self._create_kpi_card("LAST EVENT", "-", "#A78BFA")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_flashing)
        kpi_layout.addWidget(self.card_config)
        kpi_layout.addWidget(self.card_last)
        main_layout.addLayout(kpi_layout)

        # Filters Bar
        filter_frame = QFrame()
        filter_frame.setProperty("class", "card")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(10)

        # Search box
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by user, action, port, or keyword...")
        self.txt_search.textChanged.connect(self.load_activities)
        filter_layout.addWidget(self.txt_search, stretch=2)

        # Category filter
        self.cmb_filter_cat = QComboBox()
        self.cmb_filter_cat.addItem("All Categories", "ALL")
        self.cmb_filter_cat.addItem("Flashing Operations", ActivityCategory.FLASHING)
        self.cmb_filter_cat.addItem("Authentication & Session", ActivityCategory.AUTH)
        self.cmb_filter_cat.addItem("Configuration & Settings", ActivityCategory.CONFIG)
        self.cmb_filter_cat.addItem("Hardware & Port", ActivityCategory.HARDWARE)
        self.cmb_filter_cat.addItem("Sensitive Actions", ActivityCategory.SENSITIVE)
        self.cmb_filter_cat.addItem("Navigation", ActivityCategory.NAVIGATION)
        self.cmb_filter_cat.currentIndexChanged.connect(self.load_activities)
        filter_layout.addWidget(self.cmb_filter_cat, stretch=1)

        # Date Range filter
        self.cmb_filter_time = QComboBox()
        self.cmb_filter_time.addItem("All Recorded Time", "ALL")
        self.cmb_filter_time.addItem("Today Only", "TODAY")
        self.cmb_filter_time.currentIndexChanged.connect(self.load_activities)
        filter_layout.addWidget(self.cmb_filter_time, stretch=1)

        main_layout.addWidget(filter_frame)

        # Activity Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "User", "Role", "Category", "Action", "Details", "Status"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        self.table.doubleClicked.connect(self._show_details_dialog)
        main_layout.addWidget(self.table, stretch=1)

    def _create_kpi_card(self, title: str, value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"color: {color_hex}; font-size: 18px; font-weight: 800;")
        card.value_label = lbl_v

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_v)
        return card

    def load_activities(self):
        """Loads and filters activities from the local database."""
        search = self.txt_search.text().strip() or None
        cat = self.cmb_filter_cat.currentData()
        time_mode = self.cmb_filter_time.currentData()

        date_from = None
        if time_mode == "TODAY":
            from datetime import datetime
            date_from = datetime.now().strftime("%Y-%m-%d 00:00:00")

        self.activities = activity_logger.get_activities(
            limit=500,
            category=cat,
            date_from=date_from,
            search=search
        )
        self._populate_table()
        self._update_kpis()

    def _update_kpis(self):
        """Updates KPI numbers from database."""
        stats = activity_logger.get_stats_today()
        self.card_total.value_label.setText(str(stats["total_today"]))
        self.card_flashing.value_label.setText(str(stats["flashing_count"]))
        self.card_config.value_label.setText(str(stats["config_changes"]))
        self.card_last.value_label.setText(stats["last_action"])

    def _populate_table(self):
        """Populates the QTableWidget with activity rows."""
        self.table.setRowCount(len(self.activities))

        for row_idx, act in enumerate(self.activities):
            # 0: Timestamp
            item_time = QTableWidgetItem(act.get("timestamp", ""))
            item_time.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, item_time)

            # 1: User
            item_user = QTableWidgetItem(act.get("username", ""))
            item_user.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, item_user)

            # 2: Role
            item_role = QTableWidgetItem(act.get("role", ""))
            item_role.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 2, item_role)

            # 3: Category
            item_cat = QTableWidgetItem(act.get("category", ""))
            item_cat.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 3, item_cat)

            # 4: Action
            item_action = QTableWidgetItem(act.get("action", ""))
            item_action.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_action.setFont(QFont("Consolas", 9, QFont.Bold))
            self.table.setItem(row_idx, 4, item_action)

            # 5: Details
            item_details = QTableWidgetItem(act.get("details", ""))
            item_details.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row_idx, 5, item_details)

            # 6: Status Badge
            status = act.get("status", "INFO")
            item_status = QTableWidgetItem(f" {status} ")
            item_status.setTextAlignment(Qt.AlignCenter)
            self._apply_status_style(item_status, status)
            self.table.setItem(row_idx, 6, item_status)

    def _apply_status_style(self, item: QTableWidgetItem, status: str):
        if status == ActivityStatus.SUCCESS:
            item.setForeground(QColor("#10B981"))
        elif status == ActivityStatus.WARNING:
            item.setForeground(QColor("#F59E0B"))
        elif status == ActivityStatus.ERROR:
            item.setForeground(QColor("#EF4444"))
        else:
            item.setForeground(QColor("#38BDF8"))

    def _on_activity_logged(self, event_dict: dict):
        """Live slot triggered whenever a new activity is logged in the system."""
        # Simple live reload if matches current filter
        self.load_activities()

    def _show_details_dialog(self):
        """Displays full details of the double-clicked activity row."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.activities):
            return

        act = self.activities[row]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Activity Details - #{act.get('id', '')}")
        dialog.resize(550, 420)
        dialog.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title_lbl = QLabel(f"Event: {act.get('action', '')} ({act.get('category', '')})")
        title_lbl.setStyleSheet("color: #38BDF8; font-size: 16px; font-weight: bold;")
        layout.addWidget(title_lbl)

        meta_text = (
            f"Timestamp : {act.get('timestamp')}\n"
            f"User      : {act.get('username')} ({act.get('role')})\n"
            f"Status    : {act.get('status')}\n"
        )
        meta_lbl = QLabel(meta_text)
        meta_lbl.setStyleSheet("color: #94A3B8; font-family: Consolas; font-size: 12px;")
        layout.addWidget(meta_lbl)

        layout.addWidget(QLabel("Full Details / Payload:"))
        detail_box = QTextEdit()
        detail_box.setReadOnly(True)
        detail_box.setText(act.get("details", ""))
        detail_box.setStyleSheet("background-color: #020617; border: 1px solid #1E293B; color: #38BDF8; font-family: Consolas;")
        layout.addWidget(detail_box)

        btn_box = QHBoxLayout()
        btn_copy = QPushButton("Copy Details")
        btn_copy.setProperty("class", "btn-secondary")
        btn_copy.clicked.connect(lambda: detail_box.selectAll() or detail_box.copy())
        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "btn-primary")
        btn_close.clicked.connect(dialog.accept)

        btn_box.addWidget(btn_copy)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

        dialog.exec()

    def _export_csv(self):
        """Exports currently filtered logs to a CSV file."""
        if not self.activities:
            QMessageBox.information(self, "Export", "No activity logs to export.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Activity Logs", "user_activity_logs.csv", "CSV Files (*.csv)"
        )
        if not filepath:
            return

        cat = self.cmb_filter_cat.currentData()
        search = self.txt_search.text().strip() or None
        success = activity_logger.export_to_csv(filepath, category=cat, search=search)
        if success:
            QMessageBox.information(self, "Export Successful", f"Activity log exported to:\n{filepath}")
            activity_logger.log(
                category=ActivityCategory.SENSITIVE,
                action="EXPORT_ACTIVITY_CSV",
                details=f"Exported {len(self.activities)} activities to {filepath}",
                status=ActivityStatus.SUCCESS
            )
        else:
            QMessageBox.warning(self, "Export Failed", "Could not write activity log to file.")

    def _clear_logs(self):
        """Prompts operator to confirm clearing local activity logs."""
        reply = QMessageBox.question(
            self,
            "Clear Activity Logs",
            "Are you sure you want to clear all local activity logs?\n"
            "This will permanently delete activity history from this machine.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if activity_logger.clear_activities():
                self.load_activities()
                QMessageBox.information(self, "Cleared", "Local activity logs have been cleared.")
            else:
                QMessageBox.warning(self, "Error", "Failed to clear activity logs.")

