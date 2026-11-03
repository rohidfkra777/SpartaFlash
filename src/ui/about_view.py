"""
SpartaFlash - About Developer & System Information View.
Developer: Rohidfkra777
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QTextEdit, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QPixmap

from src.config.constants import (
    APP_NAME, APP_VERSION, APP_RELEASE_DATE, APP_SUBTITLE,
    DEVELOPER_NAME, DEVELOPER_GITHUB, DEVELOPER_ROLE, COPYRIGHT_NOTICE,
    ORGANIZATION_NAME, ORGANIZATION_DEPT, PROJECT_CONTEXT,
    APP_ICON_PATH
)
from src.ui.components.icon_provider import IconProvider

class AboutView(QWidget):
    """About dialog presenting verified developer identity, attribution, and architecture notes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        # Root layout with smooth ScrollArea
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Developer & Corporate Profile Card
        dev_card = QFrame()
        dev_card.setProperty("class", "card")
        dev_layout = QVBoxLayout(dev_card)
        dev_layout.setContentsMargins(20, 18, 20, 18)
        dev_layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        if APP_ICON_PATH.exists():
            lbl_icon = QLabel()
            pix = QPixmap(str(APP_ICON_PATH)).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_icon.setPixmap(pix)
            header_row.addWidget(lbl_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_app = QLabel(APP_NAME)
        lbl_app.setStyleSheet("color: #38BDF8; font-size: 24px; font-weight: 800; letter-spacing: 0.5px;")

        lbl_sub = QLabel(APP_SUBTITLE)
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 500;")

        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_sub)
        header_row.addLayout(title_box)
        header_row.addStretch()

        dev_layout.addLayout(header_row)

        # 2-Column Metadata Details Grid
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        grid_layout = QGridLayout(details_frame)
        grid_layout.setHorizontalSpacing(24)
        grid_layout.setVerticalSpacing(10)
        grid_layout.setContentsMargins(10, 10, 10, 10)

        left_items = [
            ("Lead Developer", DEVELOPER_NAME, False, ""),
            ("Organization", ORGANIZATION_NAME, False, ""),
            ("Project Context", PROJECT_CONTEXT, False, ""),
            ("Software Version", f"v{APP_VERSION} ({APP_RELEASE_DATE})", False, ""),
            ("Target Silicon", "ESP8266 & ESP32 / ESP32-C3 / ESP32-S3", False, ""),
        ]

        right_items = [
            ("Engineering Role", DEVELOPER_ROLE, False, ""),
            ("Division / Dept", ORGANIZATION_DEPT, False, ""),
            ("GitHub Profile", DEVELOPER_GITHUB, True, DEVELOPER_GITHUB),
            ("Copyright Notice", COPYRIGHT_NOTICE, False, ""),
            ("GUI Framework", "PySide6 (Qt for Python)", False, ""),
        ]

        for row_idx, (key, val, is_link, url) in enumerate(left_items):
            lbl_k = QLabel(f"{key}:")
            lbl_k.setFixedWidth(130)
            lbl_k.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 12px;")
            if is_link:
                lbl_v = QLabel(f'<a href="{url}" style="color: #38BDF8; text-decoration: none; font-weight: 700;">{val}</a>')
                lbl_v.setOpenExternalLinks(True)
            else:
                lbl_v = QLabel(val)
                lbl_v.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 600;")
            lbl_v.setWordWrap(True)
            grid_layout.addWidget(lbl_k, row_idx, 0)
            grid_layout.addWidget(lbl_v, row_idx, 1)

        for row_idx, (key, val, is_link, url) in enumerate(right_items):
            lbl_k = QLabel(f"{key}:")
            lbl_k.setFixedWidth(130)
            lbl_k.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 12px;")
            if is_link:
                lbl_v = QLabel(f'<a href="{url}" style="color: #38BDF8; text-decoration: none; font-weight: 700;">{val}</a>')
                lbl_v.setOpenExternalLinks(True)
            else:
                lbl_v = QLabel(val)
                lbl_v.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 600;")
            lbl_v.setWordWrap(True)
            grid_layout.addWidget(lbl_k, row_idx, 2)
            grid_layout.addWidget(lbl_v, row_idx, 3)

        dev_layout.addWidget(details_frame)

        # Action Button
        btn_layout = QHBoxLayout()
        btn_github = QPushButton(" Open GitHub Profile")
        btn_github.setIcon(IconProvider.get_icon("copy", color="#FFFFFF", size=15))
        btn_github.setIconSize(QSize(15, 15))
        btn_github.setProperty("class", "btn-primary")
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DEVELOPER_GITHUB)))

        btn_layout.addWidget(btn_github)
        btn_layout.addStretch()
        dev_layout.addLayout(btn_layout)

        main_layout.addWidget(dev_card)

        # System Architecture & Technical Notes Section
        lbl_notes_title = QLabel("SYSTEM ARCHITECTURE & PRODUCTION ASSURANCES")
        lbl_notes_title.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: 700; letter-spacing: 0.5px;")
        main_layout.addWidget(lbl_notes_title)

        txt_notes = QTextEdit()
        txt_notes.setReadOnly(True)
        txt_notes.setMinimumHeight(320)
        txt_notes.setStyleSheet("""
            QTextEdit {
                background-color: #090D16;
                color: #38BDF8;
                border: 1px solid #1E293B;
                border-radius: 8px;
                font-family: 'Cascadia Mono', 'Consolas', monospace;
                font-size: 12px;
                line-height: 1.4;
                padding: 14px;
            }
        """)

        notes_content = f"""SpartaFlash v{APP_VERSION} - Technical Specification & Operational Standards
Developed by {DEVELOPER_NAME} ({DEVELOPER_GITHUB})
Affiliation: {ORGANIZATION_NAME} • {ORGANIZATION_DEPT}

1. VERIFICATION BEFORE FLASHING:
   • Target chip type is dynamically probed via ROM bootloader communications.
   • Hardware compatibility between product profile (Plug / CT) and connected chip is strictly enforced.
   • Firmware image SHA-256 and Espressif image headers (0xE9) are verified before initiating programming.

2. ATOMIC RESULT DETERMINATION:
   • PASS status is asserted strictly upon successful write and verification (exit code 0 + hash match).
   • Interruptions, timeouts, or disconnection trigger immediate FAIL or CANCELLED status.
   • Flash memory is cleanly formatted prior to flashing and verified block-by-block.

3. HARDWARE SAFETY & ISOLATION:
   • AC mains isolation warnings prevent lethal high-voltage exposure during UART interfacing.
   • Mandatory 3.3V logic level checklist safeguards ESP silicon inputs.

4. TRACEABILITY & AUDIT COMPLIANCE:
   • Every flashing cycle generates an immutable SQLite transaction with microsecond precision timestamps,
     firmware SHA-256, target chip ID, hardware MAC address, operator ID, and duration.
   • Standardized CSV reports can be exported directly for manufacturing QA records."""
        txt_notes.setText(notes_content.strip())
        main_layout.addWidget(txt_notes)

        # Set scroll content
        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)
