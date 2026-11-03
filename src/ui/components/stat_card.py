"""
SpartaFlash - Neumorphic Stat Card Component.
Developer: Rohidfkra777
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class StatCard(QFrame):
    """Clean production metric KPI card."""
    def __init__(self, title: str, initial_value: str = "0", value_color: str = "#F8FAFC", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setProperty("class", "card")
        self.setStyleSheet("""
            QFrame#statCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet("color: #94A3B8; font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 10px; font-weight: 700; letter-spacing: 0.3px;")

        self.lbl_value = QLabel(initial_value)
        self.lbl_value.setStyleSheet(f"color: {value_color}; font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 800;")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def set_value(self, val: str):
        self.lbl_value.setText(val)
