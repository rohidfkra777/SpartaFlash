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
                padding: 0px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setWordWrap(False)
        self.lbl_title.setStyleSheet("color: #94A3B8; font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 9.5px; font-weight: 700; letter-spacing: 0.5px;")

        self.lbl_value = QLabel(initial_value)
        self.lbl_value.setStyleSheet(f"color: {value_color}; font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-size: 19px; font-weight: 800;")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def set_value(self, val: str):
        self.lbl_value.setText(val)
    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(60, 50)

