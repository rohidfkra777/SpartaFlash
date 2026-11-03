"""
SpartaFlash - Production History View.
Developer: Rohidfkra777
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QFileDialog, QDialog, QTextEdit
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont

from src.config.constants import PRODUCT_PLUG, PRODUCT_CT
from src.database.db_manager import db_manager
from src.database.models import ProductionRecord
from src.utils.exporter import export_records_to_csv
from src.ui.components.icon_provider import IconProvider

class HistoryView(QWidget):
    """Production log records viewer with multi-criteria filtering and CSV export."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records: List[ProductionRecord] = []
        self._base_col_widths = [185, 148, 65, 115, 140, 78, 80, 65, 74]
        self._init_ui()
        self.load_records()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Header bar
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("PRODUCTION AUDIT HISTORY")
        lbl_title.setStyleSheet("color: #38BDF8; font-size: 20px; font-weight: 800;")
        lbl_sub = QLabel("Comprehensive traceability records and compliance logs")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_export_csv = QPushButton(" Export to CSV")
        self.btn_export_csv.setIcon(IconProvider.get_icon("download", "#FFFFFF", 16))
        self.btn_export_csv.setProperty("class", "btn-primary")
        self.btn_export_csv.clicked.connect(self._export_csv)
        header_layout.addWidget(self.btn_export_csv)

        main_layout.addLayout(header_layout)

        # Filters Bar
        filter_frame = QFrame()
        filter_frame.setProperty("class", "card")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(10)

        # Search box
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by MAC, TX ID, Batch, Port...")
        self.txt_search.textChanged.connect(self.load_records)
        filter_layout.addWidget(self.txt_search, stretch=2)

        # Product filter
        self.cmb_filter_prod = QComboBox()
        self.cmb_filter_prod.addItem("All Products", "ALL")
        self.cmb_filter_prod.addItem("Plug", PRODUCT_PLUG)
        self.cmb_filter_prod.addItem("CT", PRODUCT_CT)
        self.cmb_filter_prod.currentIndexChanged.connect(self.load_records)
        filter_layout.addWidget(self.cmb_filter_prod, stretch=1)

        # Result filter
        self.cmb_filter_res = QComboBox()
        self.cmb_filter_res.addItem("All Statuses", "ALL")
        self.cmb_filter_res.addItem("PASS", "PASS")
        self.cmb_filter_res.addItem("FAIL", "FAIL")
        self.cmb_filter_res.addItem("CANCELLED", "CANCELLED")
        self.cmb_filter_res.currentIndexChanged.connect(self.load_records)
        filter_layout.addWidget(self.cmb_filter_res, stretch=1)

        # Refresh button
        btn_refresh = QPushButton(" Refresh")
        btn_refresh.setIcon(IconProvider.get_icon("refresh-cw", "#94A3B8", 14))
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.load_records)
        filter_layout.addWidget(btn_refresh)

        main_layout.addWidget(filter_frame)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "TX ID", "Date / Time", "Product", "Target Chip",
            "MAC Address", "Port", "Result", "Duration", "Details"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setHighlightSections(False)

        for col, min_w in enumerate(self._base_col_widths):
            self.table.setColumnWidth(col, min_w)

        self.table.doubleClicked.connect(self._on_row_double_clicked)
        main_layout.addWidget(self.table, stretch=1)

        # Bottom Record Count Label
        self.lbl_record_count = QLabel("Showing 0 records")
        self.lbl_record_count.setStyleSheet("color: #64748B; font-size: 11px;")
        main_layout.addWidget(self.lbl_record_count)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_column_widths()

    def showEvent(self, event):
        super().showEvent(event)
        self._adjust_column_widths()

    def _adjust_column_widths(self):
        total_base = sum(self._base_col_widths)
        available = self.table.viewport().width()
        if available > total_base:
            extra = available - total_base
            self.table.setColumnWidth(0, self._base_col_widths[0] + int(extra * 0.20))
            self.table.setColumnWidth(1, self._base_col_widths[1] + int(extra * 0.18))
            self.table.setColumnWidth(2, self._base_col_widths[2] + int(extra * 0.06))
            self.table.setColumnWidth(3, self._base_col_widths[3] + int(extra * 0.16))
            self.table.setColumnWidth(4, self._base_col_widths[4] + int(extra * 0.18))
            self.table.setColumnWidth(5, self._base_col_widths[5] + int(extra * 0.06))
            self.table.setColumnWidth(6, self._base_col_widths[6] + int(extra * 0.08))
            self.table.setColumnWidth(7, self._base_col_widths[7] + int(extra * 0.08))
            self.table.setColumnWidth(8, self._base_col_widths[8])
        else:
            for col, w in enumerate(self._base_col_widths):
                self.table.setColumnWidth(col, w)

    def load_records(self):
        """Queries database records based on current filters."""
        prod = self.cmb_filter_prod.currentData()
        res = self.cmb_filter_res.currentData()
        query = self.txt_search.text().strip()

        self.records = db_manager.get_records(
            product=prod,
            result=res,
            search_query=query,
            limit=500
        )

        self.table.setRowCount(len(self.records))
        for row, r in enumerate(self.records):
            # Helper to create styled non-editable item
            def make_item(text: str, align=Qt.AlignCenter, tooltip: Optional[str] = None):
                it = QTableWidgetItem(text)
                it.setTextAlignment(align)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if tooltip:
                    it.setToolTip(tooltip)
                return it

            # TX ID
            self.table.setItem(row, 0, make_item(r.transaction_id, Qt.AlignCenter, r.transaction_id))

            # Date/Time
            self.table.setItem(row, 1, make_item(r.start_time, Qt.AlignCenter, r.start_time))

            # Product
            self.table.setItem(row, 2, make_item(r.product_category, Qt.AlignCenter, f"Target: {r.product_category}"))

            # Target Chip
            chip_raw = r.target_chip or "-"
            chip_txt = chip_raw.replace("(Simulated)", "[SIM]")
            self.table.setItem(row, 3, make_item(chip_txt, Qt.AlignCenter, f"Chip Silicon: {chip_raw}"))

            # MAC Address
            mac_txt = r.mac_address or "N/A"
            self.table.setItem(row, 4, make_item(mac_txt, Qt.AlignCenter, f"Hardware MAC: {mac_txt}"))

            # Port
            self.table.setItem(row, 5, make_item(r.serial_port, Qt.AlignCenter, f"Serial Port: {r.serial_port}"))

            # Result Badge Item
            item_res = make_item(f"● {r.result}", Qt.AlignCenter, f"Status: {r.result}")
            res_font = item_res.font()
            res_font.setBold(True)
            item_res.setFont(res_font)
            if r.result == "PASS":
                item_res.setForeground(QColor("#10B981"))
            elif r.result == "FAIL":
                item_res.setForeground(QColor("#EF4444"))
            else:
                item_res.setForeground(QColor("#F59E0B"))
            self.table.setItem(row, 6, item_res)

            # Duration
            self.table.setItem(row, 7, make_item(f"{r.duration_seconds:.1f}s", Qt.AlignCenter))

            # Detail Button (Centered in cell container)
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(6, 4, 6, 4)
            cell_layout.setAlignment(Qt.AlignCenter)

            btn_detail = QPushButton(" View")
            btn_detail.setIcon(IconProvider.get_icon("file-text", "#38BDF8", 12))
            btn_detail.setIconSize(QSize(12, 12))
            btn_detail.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #38BDF8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 3px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    border-color: #38BDF8;
                }
            """)
            btn_detail.setCursor(Qt.PointingHandCursor)
            btn_detail.clicked.connect(lambda _, rec=r: self._show_detail(rec))
            cell_layout.addWidget(btn_detail)
            self.table.setCellWidget(row, 8, cell_widget)

        self.lbl_record_count.setText(f"Showing {len(self.records)} records (Filtered from database)")
        self._adjust_column_widths()

    def _on_row_double_clicked(self, index):
        row = index.row()
        if 0 <= row < len(self.records):
            self._show_detail(self.records[row])

    def _show_detail(self, r: ProductionRecord):
        """Displays full production transaction details dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Transaction Detail - {r.transaction_id}")
        dlg.setFixedSize(580, 480)
        dlg.setStyleSheet("QDialog { background-color: #0F172A; color: #F8FAFC; }")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl_header = QLabel(f"Transaction Record: {r.transaction_id}")
        lbl_header.setStyleSheet("color: #38BDF8; font-size: 16px; font-weight: 700;")
        layout.addWidget(lbl_header)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("""
            QTextEdit {
                background-color: #090D16;
                color: #38BDF8;
                border: 1px solid #1E293B;
                border-radius: 8px;
                font-family: 'Cascadia Mono', 'Consolas', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)

        lines = [
            f"Transaction ID      : {r.transaction_id}",
            f"Start Time          : {r.start_time}",
            f"End Time            : {r.end_time or '-'}",
            f"Duration            : {r.duration_seconds:.2f} seconds",
            f"Product Category    : {r.product_category}",
            f"Target Chip         : {r.target_chip}",
            f"MAC Address         : {r.mac_address or 'N/A'}",
            f"Serial Port         : {r.serial_port} @ {r.baudrate} baud",
            f"Firmware File       : {r.firmware_name}",
            f"Firmware Version    : {r.firmware_version or '-'}",
            f"SHA-256 Hash        : {r.firmware_hash}",
            f"Flashing Result     : {r.result}",
            f"Verification Status : {r.verification_status}",
            f"Batch ID / Name     : {r.batch_name or '-'}",
            f"Equipment ID        : {r.equipment_id or '-'}",
            f"Application Version : {r.app_version}",
            f"Operator Notes      : {r.operator_notes or '-'}",
        ]
        if r.error_message:
            lines.append(f"\n--- Error Diagnostic Details ---\n{r.error_message}")

        txt.setText("\n".join(lines))
        layout.addWidget(txt)

        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "btn-secondary")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)

        dlg.exec()

    def _export_csv(self):
        if not self.records:
            QMessageBox.information(self, "Export CSV", "No records found matching current criteria.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Production Report", "AlfaEnergy_Production_Report.csv", "CSV Files (*.csv)"
        )
        if file_path:
            out = export_records_to_csv(self.records, file_path)
            QMessageBox.information(self, "Export Successful", f"Report successfully exported to:\n{out}")
