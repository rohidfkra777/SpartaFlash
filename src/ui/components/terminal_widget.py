"""
SpartaFlash - Terminal Widget Component.
Developer: Rohidfkra777
"""

import random
import textwrap
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QCheckBox, QApplication
)
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt

SPARTABOT_QUOTES = [
    "Colok kabelnya yang pas ya kak, jangan sampai ketuker pin 3.3V sama 5V... nanti aku kepanasan! 🔥",
    "Pastikan kabel USB nancep kenceng ya! Jangan senggol-senggol meja pas flashing lagi jalan! ⚡",
    "Semangat kerjanya kak operator! Bismillah dulu biar ESP32-nya gak kena kutukan bootloop! ✨",
    "SpartaBot udah siap tempur nih! Target hari ini pantang pulang sebelum semua unit PASS! 🎯",
    "Kabel TX ke RX, kabel RX ke TX... awas jangan sampai kebalik ya kak, nanti kita saling membisu! 🔌",
    "Ngopi dulu boleh kak biar makin fokus, tapi kabel USB jangan sampai kesiram kopi ya! ☕",
    "Satu unit lagi menuju target! Santai tapi pasti, teliti demi kualitas perangkat terbaik! 🚀",
    "SpartaBot standby 24/7! Sensor energi siap dipasangkan ke dalam chip pintar! 💡",
]

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
        self.chk_autoscroll.setCursor(Qt.PointingHandCursor)
        self.chk_autoscroll.setStyleSheet("""
            QCheckBox {
                color: #94A3B8;
                font-size: 11px;
                font-weight: 500;
                spacing: 6px;
            }
            QCheckBox:hover {
                color: #F8FAFC;
            }
        """)

        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setProperty("class", "btn-secondary")
        self.btn_copy.setFixedHeight(28)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.clicked.connect(self.copy_log)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setProperty("class", "btn-secondary")
        self.btn_clear.setFixedHeight(28)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(lambda: self.clear_log(with_greeting=True))

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

        # Show initial randomized cute greeting from SpartaBot
        self.show_welcome_greeting()

    def show_welcome_greeting(self):
        """Displays randomized witty greeting from SpartaBot."""
        quote = random.choice(SPARTABOT_QUOTES)
        box_w = 54
        border_top = "╭" + "─" * (box_w - 2) + "╮"
        border_bot = "╰" + "─" * (box_w - 2) + "╯"

        header = "│  🤖 Halo Kak Operator! SpartaBot Siap Tempur! ⚡"
        header_padded = header + " " * max(0, box_w - len(header) - 1) + "│"

        lines = [border_top, header_padded]
        wrapped = textwrap.wrap(f'"{quote}"', width=box_w - 6)
        for q_line in wrapped:
            content = "│  " + q_line
            padded = content + " " * max(0, box_w - len(content) - 1) + "│"
            lines.append(padded)
        lines.append(border_bot)
        lines.append("[*] Sistem workstation siap siaga. Auto-scan port serial aktif! 🔌")
        lines.append("[*] Hubungkan kabel USB-UART ke target device lalu klik [START FLASHING]... ✨\n")

        self.txt_terminal.setPlainText("\n".join(lines))

    def append_line(self, line: str):
        self.txt_terminal.appendPlainText(line)
        if self.chk_autoscroll.isChecked():
            self.txt_terminal.moveCursor(QTextCursor.End)

    def clear_log(self, with_greeting: bool = False):
        self.txt_terminal.clear()
        if with_greeting:
            self.show_welcome_greeting()

    def copy_log(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.txt_terminal.toPlainText())
