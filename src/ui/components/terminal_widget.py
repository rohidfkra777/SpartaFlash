"""
SpartaFlash - Terminal Widget Component.
Developer: Rohidfkra777
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QCheckBox, QApplication
)
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt

class TerminalWidget(QFrame):
    """Terminal console widget for streaming esptool and flashing logs."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("terminalFrame")
        self.setProperty("class", "card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        lbl_header = QLabel("REAL-TIME PROCESS TERMINAL")
        lbl_header.setStyleSheet("color: #38BDF8; font-weight: 700; font-size: 12px; letter-spacing: 0.5px;")

        self.chk_autoscroll = QCheckBox("Auto-scroll")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setStyleSheet("color: #94A3B8; font-size: 11px;")

        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setProperty("class", "btn-secondary")
        self.btn_copy.setFixedHeight(26)
        self.btn_copy.clicked.connect(self.copy_log)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setProperty("class", "btn-secondary")
        self.btn_clear.setFixedHeight(26)
        self.btn_clear.clicked.connect(self.clear_log)

        header_layout.addWidget(lbl_header)
        header_layout.addStretch()
        header_layout.addWidget(self.chk_autoscroll)
        header_layout.addWidget(self.btn_copy)
        header_layout.addWidget(self.btn_clear)

        # Terminal text edit
        self.txt_terminal = QPlainTextEdit()
        self.txt_terminal.setObjectName("terminalLog")
        self.txt_terminal.setReadOnly(True)
        self.txt_terminal.setMaximumBlockCount(2000)

        layout.addLayout(header_layout)
        layout.addWidget(self.txt_terminal)

    def append_line(self, line: str):
        self.txt_terminal.appendPlainText(line)
        if self.chk_autoscroll.isChecked():
            self.txt_terminal.moveCursor(QTextCursor.End)

    def clear_log(self):
        self.txt_terminal.clear()

    def copy_log(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.txt_terminal.toPlainText())
