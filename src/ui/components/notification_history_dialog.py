"""
SpartaFlash - Incident Notification & System Event History Audit Dialog.
Developer: Rohidfkra777

Provides operators and facility engineers with an immutable audit trail of:
- Device connection drops (OFFLINE events)
- Network connectivity recoveries (InternetRestored events)
- LittleFS flash buffer replays (SyncComplete events)
- Downtime durations and buffered telemetry record quantities.
- Detailed modal popup inspection with one-click clipboard copying.
"""

import csv
from typing import Optional, List, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QFileDialog, QTextEdit, QGridLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication

from src.database.db_manager import db_manager
from src.ui.components.icon_provider import IconProvider


class NotificationDetailDialog(QDialog):
    """
    Focused modal dialog to inspect complete incident details, hardware telemetry metadata,
    and the full un-truncated message with one-click clipboard copying.
    """

    def __init__(self, event_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.event_data = event_data
        dev_name = event_data.get("device_name", "Perangkat")
        self.setWindowTitle(f"Detail Insiden - {dev_name}")
        self.resize(560, 440)
        self.setMinimumSize(460, 360)

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
                background: transparent;
                border: none;
            }
            QFrame#metaCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QTextEdit {
                background-color: #0B1120;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                font-size: 12px;
                line-height: 1.6;
                padding: 10px;
                selection-background-color: #1E293B;
                selection-color: #38BDF8;
            }
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Header Banner with Status Badge
        etype = self.event_data.get("event_type", "").upper()
        if etype == "OFFLINE":
            badge_title = "⚠️ TERPUTUS DARI JARINGAN (OFFLINE)"
            b_color = "#EF4444"
            bg_color = "#450A0A"
        elif etype == "RESTORED":
            badge_title = "🟢 INTERNET PULIH (REPLAY BUFFER DIMULAI)"
            b_color = "#10B981"
            bg_color = "#064E3B"
        elif etype == "SYNC_COMPLETE":
            badge_title = "✅ SINKRONISASI BUFFER SELESAI"
            b_color = "#38BDF8"
            bg_color = "#0C4A6E"
        else:
            badge_title = f"ℹ️ EVENT: {etype}"
            b_color = "#94A3B8"
            bg_color = "#1E293B"

        banner = QFrame()
        banner.setObjectName("statusBanner")
        banner.setStyleSheet(f"""
            QFrame#statusBanner {{
                background-color: {bg_color};
                border: 1px solid {b_color};
                border-radius: 8px;
                padding: 10px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(4)

        lbl_b_title = QLabel(badge_title)
        lbl_b_title.setStyleSheet(f"color: {b_color}; font-weight: 800; font-size: 13px;")
        
        lbl_b_time = QLabel(f"Waktu Kejadian: {self.event_data.get('timestamp', '-')}")
        lbl_b_time.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        
        banner_layout.addWidget(lbl_b_title)
        banner_layout.addWidget(lbl_b_time)
        layout.addWidget(banner)

        # 2. Metadata Grid Card
        meta_card = QFrame()
        meta_card.setObjectName("metaCard")
        grid = QGridLayout(meta_card)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        # Row 0: Device & MAC
        dev_name = self.event_data.get("device_name", "-")
        mac = self.event_data.get("mac_address", "-")
        grid.addWidget(self._make_label_caption("Perangkat:"), 0, 0)
        grid.addWidget(self._make_label_value(dev_name, color="#F8FAFC", bold=True), 0, 1)

        grid.addWidget(self._make_label_caption("MAC Address:"), 0, 2)
        grid.addWidget(self._make_label_value(mac, color="#94A3B8", font_family="Consolas"), 0, 3)

        # Row 1: Location & Downtime / Buffer
        loc = self.event_data.get("location_desc", "") or "-"
        dt_sec = self.event_data.get("downtime_sec", 0)
        rec_cnt = self.event_data.get("records_count", 0)

        dt_str = "-"
        if dt_sec > 0:
            m = dt_sec // 60
            s = dt_sec % 60
            dt_str = f"{m}m {s}s" if m > 0 else f"{s}s"

        buf_str = f"{rec_cnt} rekaman" if rec_cnt > 0 else "-"

        grid.addWidget(self._make_label_caption("Lokasi / Panel:"), 1, 0)
        grid.addWidget(self._make_label_value(loc, color="#38BDF8", bold=True), 1, 1)

        grid.addWidget(self._make_label_caption("Downtime:"), 1, 2)
        grid.addWidget(self._make_label_value(dt_str, color="#F59E0B" if dt_str != "-" else "#94A3B8"), 1, 3)

        # Row 2: Data Buffer
        grid.addWidget(self._make_label_caption("Data Buffer:"), 2, 0)
        grid.addWidget(self._make_label_value(buf_str, color="#34D399" if buf_str != "-" else "#94A3B8"), 2, 1)

        layout.addWidget(meta_card)

        # 3. Message Text Box
        lbl_msg_title = QLabel("📋 Detail Pesan Lengkap:")
        lbl_msg_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        layout.addWidget(lbl_msg_title)

        self.txt_message = QTextEdit()
        self.txt_message.setReadOnly(True)
        self.txt_message.setPlainText(self.event_data.get("message", ""))
        layout.addWidget(self.txt_message, stretch=1)

        # 4. Footer & Action Buttons
        footer = QHBoxLayout()

        self.lbl_copied = QLabel("")
        self.lbl_copied.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 700;")
        footer.addWidget(self.lbl_copied)
        footer.addStretch()

        btn_copy = QPushButton("📋 Salin Pesan")
        btn_copy.setToolTip("Salin ringkasan dan detail insiden ke clipboard Windows")
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #065F46;
                color: #A7F3D0;
                border: 1px solid #059669;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        btn_copy.clicked.connect(self._copy_to_clipboard)
        footer.addWidget(btn_copy)

        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)

        layout.addLayout(footer)

    def _make_label_caption(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
        return lbl

    def _make_label_value(self, text: str, color: str = "#F8FAFC", bold: bool = False, font_family: str = "") -> QLabel:
        lbl = QLabel(text)
        style = f"color: {color}; font-size: 11px;"
        if bold:
            style += " font-weight: 700;"
        if font_family:
            style += f" font-family: {font_family};"
        lbl.setStyleSheet(style)
        return lbl

    def _copy_to_clipboard(self):
        """Copies structured incident summary to system clipboard with visual confirmation."""
        clipboard = QGuiApplication.clipboard()
        msg = self.event_data.get("message", "")
        summary_text = (
            f"[{self.event_data.get('timestamp')}] {self.event_data.get('event_type')}\n"
            f"Perangkat : {self.event_data.get('device_name')} ({self.event_data.get('mac_address')})\n"
            f"Lokasi    : {self.event_data.get('location_desc') or '-'}\n"
            f"Pesan     : {msg}"
        )
        clipboard.setText(summary_text)
        self.lbl_copied.setText("✓ Tersalin ke clipboard!")
        QTimer.singleShot(2500, lambda: self.lbl_copied.setText(""))


class NotificationHistoryDialog(QDialog):
    """
    Industrial audit dialog for reviewing device connection incidents and LittleFS buffer sync logs.
    Includes instant search, event category filtering, CSV exporting, log clearing,
    and single-click/double-click detail popup modal.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Riwayat Notifikasi & Insiden Sistem")
        self.resize(920, 580)
        self.setMinimumSize(720, 440)
        self._current_events: List[Dict[str, Any]] = []

        self._init_ui()
        self._load_data()

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
            QLineEdit, QComboBox {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                color: #F8FAFC;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #38BDF8;
            }
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QTableWidget {
                background-color: #0B1120;
                border: 1px solid #1E293B;
                border-radius: 6px;
                gridline-color: #1E293B;
                color: #F8FAFC;
                selection-background-color: #1E293B;
                selection-color: #38BDF8;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #334155;
                font-weight: 700;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Section
        header_layout = QHBoxLayout()
        header_text_box = QVBoxLayout()
        
        lbl_title = QLabel("📋 LOG RIWAYAT NOTIFIKASI & INSIDEN JARINGAN")
        lbl_title.setStyleSheet("color: #38BDF8; font-size: 15px; font-weight: 800;")
        
        lbl_subtitle = QLabel("Rekaman insiden koneksi terputus, internet pulih, dan sinkronisasi offline buffer LittleFS")
        lbl_subtitle.setStyleSheet("color: #94A3B8; font-size: 11px;")
        
        header_text_box.addWidget(lbl_title)
        header_text_box.addWidget(lbl_subtitle)
        header_layout.addLayout(header_text_box)
        header_layout.addStretch()

        btn_refresh = QPushButton(" 🔄 Refresh")
        btn_refresh.clicked.connect(self._load_data)
        header_layout.addWidget(btn_refresh)

        layout.addLayout(header_layout)

        # Filter & Search Toolbar
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 8, 10, 8)
        filter_layout.setSpacing(10)

        # Search field
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Cari perangkat, MAC, lokasi, atau pesan...")
        self.txt_search.textChanged.connect(self._load_data)
        filter_layout.addWidget(self.txt_search, stretch=3)

        # Event type combo
        self.cmb_filter_type = QComboBox()
        self.cmb_filter_type.addItem("Semua Event", "ALL")
        self.cmb_filter_type.addItem("⚠️ Terputus (OFFLINE)", "OFFLINE")
        self.cmb_filter_type.addItem("🟢 Internet Pulih (RESTORED)", "RESTORED")
        self.cmb_filter_type.addItem("✅ Sinkronisasi Selesai (SYNC_COMPLETE)", "SYNC_COMPLETE")
        self.cmb_filter_type.currentIndexChanged.connect(self._load_data)
        filter_layout.addWidget(self.cmb_filter_type, stretch=2)

        # Export CSV Button
        btn_export = QPushButton("📥 Export CSV")
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: #065F46;
                color: #A7F3D0;
                border: 1px solid #059669;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        btn_export.clicked.connect(self._export_to_csv)
        filter_layout.addWidget(btn_export)

        # Clear History Button
        btn_clear = QPushButton("🗑️ Hapus Riwayat")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #450A0A;
                color: #FCA5A5;
                border: 1px solid #991B1B;
            }
            QPushButton:hover {
                background-color: #7F1D1D;
            }
        """)
        btn_clear.clicked.connect(self._clear_history)
        filter_layout.addWidget(btn_clear)

        layout.addWidget(filter_frame)

        # Log Table
        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(7)
        self.table_logs.setHorizontalHeaderLabels([
            "Waktu", "Status Event", "Perangkat", "MAC Address", "Lokasi / Panel", "Downtime / Buffer", "Detail Pesan"
        ])
        self.table_logs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table_logs.verticalHeader().setVisible(False)
        self.table_logs.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_logs.setAlternatingRowColors(True)
        self.table_logs.setCursor(Qt.PointingHandCursor)

        # Connect cell click and double click to open detail popup
        self.table_logs.cellDoubleClicked.connect(self._on_table_cell_double_clicked)
        self.table_logs.cellClicked.connect(self._on_table_cell_clicked)

        layout.addWidget(self.table_logs)

        # Footer Bar with Tips and Controls
        footer_layout = QHBoxLayout()
        
        info_box = QVBoxLayout()
        self.lbl_summary = QLabel("Menampilkan 0 insiden")
        self.lbl_summary.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        
        lbl_hint = QLabel("💡 Tip: Klik atau klik ganda baris / kolom 'Detail Pesan' untuk membuka rincian lengkap & salin teks.")
        lbl_hint.setStyleSheet("color: #64748B; font-size: 10px; font-style: italic;")
        
        info_box.addWidget(self.lbl_summary)
        info_box.addWidget(lbl_hint)
        footer_layout.addLayout(info_box)

        footer_layout.addStretch()

        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        layout.addLayout(footer_layout)

    def _load_data(self):
        """Fetches events from database matching search and category filter."""
        event_type = self.cmb_filter_type.currentData()
        search_text = self.txt_search.text().strip() or None

        self._current_events = db_manager.get_system_events(
            limit=300,
            event_type=event_type,
            search=search_text
        )

        self.table_logs.setRowCount(len(self._current_events))

        for row, evt in enumerate(self._current_events):
            # 0: Timestamp
            t_item = QTableWidgetItem(evt.get("timestamp", ""))
            t_item.setTextAlignment(Qt.AlignCenter)
            t_item.setForeground(QColor("#94A3B8"))
            self.table_logs.setItem(row, 0, t_item)

            # 1: Status Event
            etype = evt.get("event_type", "").upper()
            badge_text = etype
            badge_color = "#94A3B8"
            if etype == "OFFLINE":
                badge_text = "⚠️ TERPUTUS"
                badge_color = "#EF4444"
            elif etype == "RESTORED":
                badge_text = "🟢 PULIH"
                badge_color = "#10B981"
            elif etype == "SYNC_COMPLETE":
                badge_text = "✅ SINKRON"
                badge_color = "#38BDF8"

            e_item = QTableWidgetItem(badge_text)
            e_item.setTextAlignment(Qt.AlignCenter)
            e_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            e_item.setForeground(QColor(badge_color))
            self.table_logs.setItem(row, 1, e_item)

            # 2: Perangkat
            dev_name = evt.get("device_name", "")
            d_item = QTableWidgetItem(dev_name)
            d_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table_logs.setItem(row, 2, d_item)

            # 3: MAC Address
            mac = evt.get("mac_address", "")
            m_item = QTableWidgetItem(mac)
            m_item.setFont(QFont("Consolas", 9))
            m_item.setTextAlignment(Qt.AlignCenter)
            m_item.setForeground(QColor("#64748B"))
            self.table_logs.setItem(row, 3, m_item)

            # 4: Lokasi / Panel
            loc = evt.get("location_desc", "") or "-"
            l_item = QTableWidgetItem(loc)
            l_item.setForeground(QColor("#38BDF8") if loc != "-" else QColor("#64748B"))
            self.table_logs.setItem(row, 4, l_item)

            # 5: Downtime / Buffer
            dt_sec = evt.get("downtime_sec", 0)
            rec_cnt = evt.get("records_count", 0)
            meta_parts = []
            if dt_sec > 0:
                mins = dt_sec // 60
                secs = dt_sec % 60
                meta_parts.append(f"{mins}m {secs}s" if mins > 0 else f"{secs}s")
            if rec_cnt > 0:
                meta_parts.append(f"{rec_cnt} rec")
            meta_str = " | ".join(meta_parts) if meta_parts else "-"

            dt_item = QTableWidgetItem(meta_str)
            dt_item.setTextAlignment(Qt.AlignCenter)
            dt_item.setForeground(QColor("#F59E0B") if meta_str != "-" else QColor("#64748B"))
            self.table_logs.setItem(row, 5, dt_item)

            # 6: Detail Pesan
            msg = evt.get("message", "")
            msg_item = QTableWidgetItem(msg)
            msg_item.setToolTip(f"{msg}\n(Klik untuk melihat rincian lengkap)")
            self.table_logs.setItem(row, 6, msg_item)

        self.lbl_summary.setText(f"Menampilkan {len(self._current_events)} insiden tercatat pada database audit.")

    def _on_table_cell_double_clicked(self, row: int, column: int):
        """Opens detail modal when any cell in row is double-clicked."""
        self._show_detail_dialog(row)

    def _on_table_cell_clicked(self, row: int, column: int):
        """Opens detail modal if the 'Detail Pesan' column (index 6) is clicked."""
        if column == 6:
            self._show_detail_dialog(row)

    def _show_detail_dialog(self, row: int):
        """Instantiates and displays the incident detail modal dialog."""
        if 0 <= row < len(self._current_events):
            event_data = self._current_events[row]
            dlg = NotificationDetailDialog(event_data, parent=self)
            dlg.exec()

    def _export_to_csv(self):
        """Exports currently filtered logs to a standard CSV file."""
        if self.table_logs.rowCount() == 0:
            QMessageBox.information(self, "Export CSV", "Tidak ada data insiden untuk diekspor.")
            return

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"AlfaEnergy_Notification_History_{now_str}.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Log Riwayat Insiden (CSV)",
            default_filename,
            "CSV Files (*.csv)"
        )

        if not filepath:
            return

        try:
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Write header
                headers = [
                    self.table_logs.horizontalHeaderItem(col).text()
                    for col in range(self.table_logs.columnCount())
                ]
                writer.writerow(headers)

                # Write rows
                for row in range(self.table_logs.rowCount()):
                    row_data = [
                        self.table_logs.item(row, col).text() if self.table_logs.item(row, col) else ""
                        for col in range(self.table_logs.columnCount())
                    ]
                    writer.writerow(row_data)

            QMessageBox.information(
                self,
                "Export Berhasil",
                f"Log riwayat berhasil diekspor ke:\n{filepath}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Gagal Export CSV",
                f"Terjadi kesalahan saat menyimpan file CSV:\n{str(e)}"
            )

    def _clear_history(self):
        """Asks for operator confirmation before clearing all audit logs."""
        reply = QMessageBox.question(
            self,
            "Konfirmasi Hapus Riwayat",
            "Apakah Anda yakin ingin MENGHAPUS SELURUH riwayat notifikasi dan log insiden sistem?\n\n"
            "Tindakan ini tidak dapat dibatalkan.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db_manager.clear_system_events()
            self._load_data()
