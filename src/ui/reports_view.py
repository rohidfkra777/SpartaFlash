"""
SpartaFlash - Batch Reports & Production Analytics View.
Developer: Rohidfkra777
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QFrame, QTextEdit,
    QMessageBox, QFileDialog
)
from src.database.db_manager import db_manager
from src.utils.exporter import generate_batch_summary_text, export_records_to_csv
from src.ui.components.stat_card import StatCard
from src.ui.components.icon_provider import IconProvider

class ReportsView(QWidget):
    """Batch production analytics and summary report generator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_batches()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("PRODUCTION BATCH ANALYTICS")
        lbl_title.setStyleSheet("color: #38BDF8; font-size: 20px; font-weight: 800;")
        lbl_sub = QLabel("Batch KPI aggregation, quality yield metrics, and formal reporting")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_export_summary = QPushButton(" Export Summary TXT")
        self.btn_export_summary.setIcon(IconProvider.get_icon("file-text", "#94A3B8", 16))
        self.btn_export_summary.setProperty("class", "btn-secondary")
        self.btn_export_summary.clicked.connect(self._export_summary)
        header_layout.addWidget(self.btn_export_summary)

        self.btn_export_batch_csv = QPushButton(" Export Batch CSV")
        self.btn_export_batch_csv.setIcon(IconProvider.get_icon("download", "#FFFFFF", 16))
        self.btn_export_batch_csv.setProperty("class", "btn-primary")
        self.btn_export_batch_csv.clicked.connect(self._export_batch_csv)
        header_layout.addWidget(self.btn_export_batch_csv)

        main_layout.addLayout(header_layout)

        # Batch Selection Bar
        batch_bar = QFrame()
        batch_bar.setProperty("class", "card")
        batch_layout = QHBoxLayout(batch_bar)
        batch_layout.setContentsMargins(12, 10, 12, 10)
        batch_layout.setSpacing(12)

        lbl_select_batch = QLabel("Select Production Batch:")
        lbl_select_batch.setStyleSheet("color: #F8FAFC; font-weight: 600;")
        batch_layout.addWidget(lbl_select_batch)

        self.cmb_batch = QComboBox()
        self.cmb_batch.currentIndexChanged.connect(self.calculate_batch_kpis)
        batch_layout.addWidget(self.cmb_batch, stretch=1)

        btn_refresh = QPushButton(" Refresh Batches")
        btn_refresh.setIcon(IconProvider.get_icon("refresh-cw", "#94A3B8", 14))
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.refresh_batches)
        batch_layout.addWidget(btn_refresh)

        main_layout.addWidget(batch_bar)

        # KPI Summary Cards
        kpi_layout = QHBoxLayout()
        self.card_total = StatCard("Batch Total Units", "0", "#F8FAFC")
        self.card_pass = StatCard("Total Passed", "0", "#10B981")
        self.card_fail = StatCard("Total Failed", "0", "#EF4444")
        self.card_rate = StatCard("Quality Yield", "0.0%", "#38BDF8")
        self.card_duration = StatCard("Avg Flash Time", "0.0s", "#FBBF24")

        for card in [self.card_total, self.card_pass, self.card_fail, self.card_rate, self.card_duration]:
            card.setMinimumWidth(115)
            kpi_layout.addWidget(card)

        main_layout.addLayout(kpi_layout)

        # Formatted Summary Text View
        self.txt_summary = QTextEdit()
        self.txt_summary.setReadOnly(True)
        self.txt_summary.setStyleSheet("""
            QTextEdit {
                background-color: #090D16;
                color: #38BDF8;
                border: 1px solid #1E293B;
                border-radius: 8px;
                font-family: 'Cascadia Mono', 'Consolas', monospace;
                font-size: 12px;
                padding: 14px;
            }
        """)
        main_layout.addWidget(self.txt_summary, stretch=1)

    def refresh_batches(self):
        self.cmb_batch.clear()
        self.cmb_batch.addItem("All Production Batches (Aggregate)", "")
        batches = db_manager.get_batches()
        for b in batches:
            self.cmb_batch.addItem(f"Batch: {b}", b)
        self.calculate_batch_kpis()

    def calculate_batch_kpis(self):
        batch_id = self.cmb_batch.currentData()
        stats = db_manager.get_statistics(batch_name=batch_id if batch_id else None)

        self.card_total.set_value(str(stats["total"]))
        self.card_pass.set_value(str(stats["passed"]))
        self.card_fail.set_value(str(stats["failed"]))
        self.card_rate.set_value(f"{stats['pass_rate']}%")
        self.card_duration.set_value(f"{stats['avg_duration']}s")

        summary_text = generate_batch_summary_text(stats, batch_id)
        self.txt_summary.setText(summary_text)

    def _export_summary(self):
        batch_id = self.cmb_batch.currentData()
        stats = db_manager.get_statistics(batch_name=batch_id if batch_id else None)
        text = generate_batch_summary_text(stats, batch_id)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Batch Summary", "AlfaEnergy_Batch_Summary.txt", "Text Files (*.txt)"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "Export Successful", f"Batch summary saved to:\n{file_path}")

    def _export_batch_csv(self):
        batch_id = self.cmb_batch.currentData()
        records = db_manager.get_records(limit=2000)
        if batch_id:
            records = [r for r in records if r.batch_name == batch_id]

        if not records:
            QMessageBox.information(self, "Export Batch CSV", "No records found in selected batch.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Batch CSV Report", f"AlfaEnergy_Batch_{batch_id or 'All'}.csv", "CSV Files (*.csv)"
        )
        if file_path:
            out = export_records_to_csv(records, file_path)
            QMessageBox.information(self, "Export Successful", f"Batch CSV saved to:\n{out}")
