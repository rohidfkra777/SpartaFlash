"""
SpartaFlash - Main Operator Dashboard View.
Developer: Rohidfkra777
"""

from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QProgressBar,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QImage

from src.config.constants import (
    PRODUCT_PLUG, PRODUCT_CT, PRODUCT_CONFIGS,
    STATUS_READY, STATUS_ERASING, STATUS_FLASHING, STATUS_VERIFYING, STATUS_PASS, STATUS_FAIL, STATUS_CANCELLED,
    DEVELOPER_FOOTER_TEXT, DEVELOPER_GITHUB, APP_VERSION
)
from src.config.settings import settings_manager
from src.services.firmware_service import FirmwareService, FirmwareInfo
from src.services.serial_service import SerialService, SerialPortInfo
from src.services.driver_service import DriverService
from src.services.flasher_worker import FlasherWorker
from src.services.cloud_firmware_service import CloudFirmwareService
from src.services.cloud_sync_worker import CloudSyncWorker
from src.utils.security_vault import SecurityVault
from src.database.db_manager import db_manager
from src.database.models import ProductionRecord
from src.ui.components.stat_card import StatCard
from src.ui.components.terminal_widget import TerminalWidget
from src.ui.components.safety_dialog import SafetyDialog
from src.ui.components.icon_provider import IconProvider
from src.services.auth_service import auth_service

from src.services.activity_log_service import activity_logger, ActivityCategory, ActivityStatus
from src.services.sound_service import sound_service

class DashboardView(QWidget):
    """Main industrial flashing dashboard for workstation operators."""

    sig_request_history = Signal()
    sig_request_settings = Signal()
    sig_request_monitor = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: Optional[FlasherWorker] = None
        self.cloud_worker: Optional[CloudSyncWorker] = None
        self.current_firmware_info: Optional[FirmwareInfo] = None
        self.custom_firmware_path: Optional[Path] = None

        self._init_ui()
        self._update_product_hero_image()
        self.refresh_ports()
        self.update_firmware_status()
        self.refresh_stats()
        self._check_cloud_updates_silently()
        # Automated zero-touch USB driver check & installation
        DriverService.auto_ensure_drivers_installed(callback_on_installed=self.refresh_ports)
        self.update_permissions()
        auth_service.sig_auth_state_changed.connect(self.update_permissions)

        # Background automated port monitor (auto-scan every 1.2s without manual refresh button)
        self._port_scan_timer = QTimer(self)
        self._port_scan_timer.setInterval(1200)
        self._port_scan_timer.timeout.connect(self._auto_scan_ports)
        self._port_scan_timer.start()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Bar: Clean Title & Pipeline Subtitle
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title_box.setContentsMargins(0, 0, 0, 0)
        lbl_dash_title = QLabel("Station Flasher")
        lbl_dash_title.setStyleSheet("color: #38BDF8; font-size: 18px; font-weight: 800; letter-spacing: 0.8px; font-family: 'Segoe UI', -apple-system, sans-serif;")
        lbl_dash_sub = QLabel("Automated Firmware Flashing & Hardware Verification Pipeline")
        lbl_dash_sub.setStyleSheet("color: #94A3B8; font-size: 11.5px; font-weight: 500; font-family: 'Segoe UI', -apple-system, sans-serif;")
        title_box.addWidget(lbl_dash_title)
        title_box.addWidget(lbl_dash_sub)
        title_box.addStretch()

        top_layout.addLayout(title_box)
        top_layout.addStretch()

        main_layout.addLayout(top_layout)

        # 2. Main Work Area: Left Control Panel (Settings & Firmware), Right Terminal & Status
        work_layout = QHBoxLayout()
        work_layout.setSpacing(16)

        # LEFT COLUMN: Configuration, Port, Firmware, Start Action
        left_panel = QFrame()
        left_panel.setProperty("class", "card")
        left_panel.setFixedWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        # A. Section 1: TARGET PRODUK PRODUKSI (AUTO-LOCKED)
        sec_prod_header = QHBoxLayout()
        lbl_sec_prod = QLabel("1. TARGET PRODUK")
        lbl_sec_prod.setProperty("class", "card-title")
        sec_prod_header.addWidget(lbl_sec_prod)

        lbl_prod_hint = QLabel("▼ PILIH PRODUK")
        lbl_prod_hint.setStyleSheet("""
            color: #38BDF8;
            font-size: 10px;
            font-weight: 800;
            background-color: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.4);
            border-radius: 4px;
            padding: 2px 7px;
        """)
        sec_prod_header.addWidget(lbl_prod_hint, alignment=Qt.AlignRight | Qt.AlignVCenter)
        left_layout.addLayout(sec_prod_header)

        self.cmb_product = QComboBox()
        self.cmb_product.setObjectName("targetProductSelector")
        self.cmb_product.setCursor(Qt.PointingHandCursor)
        self.cmb_product.setIconSize(QSize(22, 22))

        icon_plug = IconProvider.get_icon("zap", color="#38BDF8", size=22)
        icon_ct = IconProvider.get_icon("cpu", color="#F59E0B", size=22)

        self.cmb_product.addItem(icon_plug, "  Sparta Smart Plug", PRODUCT_PLUG)
        self.cmb_product.addItem(icon_ct, "  Sparta Smart CT", PRODUCT_CT)
        self.cmb_product.currentIndexChanged.connect(self._on_product_changed)
        left_layout.addWidget(self.cmb_product)

        # Cloud OTA Synchronization status & action row
        cloud_sync_row = QHBoxLayout()
        cloud_sync_row.setContentsMargins(0, 2, 0, 2)
        cloud_sync_row.setSpacing(6)

        self.lbl_cloud_status = QLabel("● Cloud OTA: Menghubungkan...")
        self.lbl_cloud_status.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        cloud_sync_row.addWidget(self.lbl_cloud_status, stretch=1)

        self.btn_sync_cloud = QPushButton(" Cek Cloud")
        self.btn_sync_cloud.setIcon(IconProvider.get_icon("refresh-cw", "#38BDF8", 12))
        self.btn_sync_cloud.setIconSize(QSize(12, 12))
        self.btn_sync_cloud.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
                border-color: #38BDF8;
            }
            QPushButton:disabled {
                background-color: #0F172A;
                color: #64748B;
                border-color: #1E293B;
            }
        """)
        self.btn_sync_cloud.setCursor(Qt.PointingHandCursor)
        self.btn_sync_cloud.clicked.connect(self._on_manual_sync_clicked)
        cloud_sync_row.addWidget(self.btn_sync_cloud)

        left_layout.addLayout(cloud_sync_row)

        # Product Hero Preview Banner (Concept 2)
        self.frame_hero_prod = QFrame()
        self.frame_hero_prod.setObjectName("frameHeroProd")
        self.frame_hero_prod.setStyleSheet("""
            QFrame#frameHeroProd {
                background-color: #000000;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        hero_layout = QVBoxLayout(self.frame_hero_prod)
        hero_layout.setContentsMargins(6, 6, 6, 6)
        hero_layout.setSpacing(0)

        self.lbl_hero_img = QLabel()
        self.lbl_hero_img.setAlignment(Qt.AlignCenter)
        self.lbl_hero_img.setFixedHeight(130)
        self.lbl_hero_img.setStyleSheet("background-color: transparent;")
        hero_layout.addWidget(self.lbl_hero_img)

        left_layout.addWidget(self.frame_hero_prod)

        # Technical Spec Grid: Profile & Firmware Integrity (2-Column Key-Value)
        self.frame_fw = QFrame()
        self.frame_fw.setObjectName("frameFwAutoLock")
        self.frame_fw.setStyleSheet("""
            QFrame#frameFwAutoLock {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        fw_box = QVBoxLayout(self.frame_fw)
        fw_box.setSpacing(6)
        fw_box.setContentsMargins(12, 10, 12, 10)

        # Header Row: Clean Title + Official Status Badge
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 2)
        lbl_spec_title = QLabel("DEVICE PROFILE & FIRMWARE SPEC")
        lbl_spec_title.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        header_row.addWidget(lbl_spec_title)
        header_row.addStretch()
        fw_box.addLayout(header_row)

        # Separator line
        spec_sep = QFrame()
        spec_sep.setFrameShape(QFrame.HLine)
        spec_sep.setStyleSheet("background-color: #1E293B; max-height: 1px; border: none;")
        fw_box.addWidget(spec_sep)

        # 2-Column Key-Value Grid
        grid_spec = QGridLayout()
        grid_spec.setHorizontalSpacing(10)
        grid_spec.setVerticalSpacing(5)
        grid_spec.setContentsMargins(0, 2, 0, 2)

        def make_spec_key(text: str) -> QLabel:
            k = QLabel(text)
            k.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
            k.setFixedWidth(100)
            return k

        # Row 0: Target Chipset
        grid_spec.addWidget(make_spec_key("Chip Target"), 0, 0)
        self.lbl_fw_chip = QLabel("-")
        self.lbl_fw_chip.setStyleSheet("color: #F8FAFC; font-size: 11px; font-weight: 600;")
        grid_spec.addWidget(self.lbl_fw_chip, 0, 1)

        # Row 1: Power & Wiring
        grid_spec.addWidget(make_spec_key("Tegangan/Logic"), 1, 0)
        self.lbl_power_spec = QLabel("-")
        self.lbl_power_spec.setStyleSheet("color: #FCD34D; font-size: 11px; font-weight: 600;")
        grid_spec.addWidget(self.lbl_power_spec, 1, 1)

        # Row 2: Firmware Image
        grid_spec.addWidget(make_spec_key("Firmware"), 2, 0)
        self.lbl_fw_name = QLabel("Memuat...")
        self.lbl_fw_name.setStyleSheet("color: #F8FAFC; font-size: 11px; font-weight: 600;")
        grid_spec.addWidget(self.lbl_fw_name, 2, 1)

        # Row 3: Checksum
        grid_spec.addWidget(make_spec_key("Integritas"), 3, 0)
        self.lbl_fw_hash = QLabel("-")
        self.lbl_fw_hash.setStyleSheet("color: #94A3B8; font-size: 10.5px; font-family: 'Consolas', monospace;")
        grid_spec.addWidget(self.lbl_fw_hash, 3, 1)

        # Row 4: Cloud Sync
        grid_spec.addWidget(make_spec_key("Sinkronisasi"), 4, 0)
        self.lbl_fw_source = QLabel("-")
        self.lbl_fw_source.setStyleSheet("color: #38BDF8; font-size: 10.5px; font-weight: 500;")
        grid_spec.addWidget(self.lbl_fw_source, 4, 1)

        self.lbl_fw_status = QLabel("")
        self.lbl_fw_status.setVisible(False)

        fw_box.addLayout(grid_spec)
        left_layout.addWidget(self.frame_fw)
        left_layout.addSpacing(4)

        # B. Section 2: SERIAL PORT & FLASHING
        lbl_sec_port = QLabel("2. KONEKSI USB & FLASHING")
        lbl_sec_port.setProperty("class", "card-title")
        left_layout.addWidget(lbl_sec_port)

        self.cmb_ports = QComboBox()
        self.cmb_ports.currentIndexChanged.connect(self._on_port_changed)
        left_layout.addWidget(self.cmb_ports)

        # Hidden programmatic button preserved for API & test backward compatibility
        self.btn_refresh_ports = QPushButton(" Scan Port")
        self.btn_refresh_ports.setVisible(False)
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)

        self.lbl_port_diag = QLabel("No port detected. Connect USB-UART cable.")
        self.lbl_port_diag.setWordWrap(True)
        self.lbl_port_diag.setStyleSheet("color: #64748B; font-size: 11px;")
        left_layout.addWidget(self.lbl_port_diag)

        left_layout.addStretch()

        # Action Trigger Buttons
        self.btn_start = QPushButton("  START FLASHING")
        self.btn_start.setIcon(IconProvider.get_icon("zap", color="#FFFFFF", size=20))
        self.btn_start.setIconSize(QSize(20, 20))
        self.btn_start.setObjectName("btnStartFlash")
        self.btn_start.setMinimumHeight(48)
        self.btn_start.clicked.connect(self.start_flashing)

        self.btn_cancel = QPushButton("  CANCEL PROCESS")
        self.btn_cancel.setIcon(IconProvider.get_icon("x-circle", color="#FFFFFF", size=20))
        self.btn_cancel.setIconSize(QSize(20, 20))
        self.btn_cancel.setObjectName("btnCancelFlash")
        self.btn_cancel.setMinimumHeight(48)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_flashing)

        left_layout.addWidget(self.btn_start)
        left_layout.addWidget(self.btn_cancel)

        # Quick Links
        self.links_layout = QHBoxLayout()
        self.btn_open_hist = QPushButton(" Production History")
        self.btn_open_hist.setIcon(IconProvider.get_icon("history", color="#94A3B8", size=14))
        self.btn_open_hist.setIconSize(QSize(14, 14))
        self.btn_open_hist.setProperty("class", "btn-secondary")
        self.btn_open_hist.clicked.connect(self.sig_request_history.emit)

        self.btn_open_sett = QPushButton(" Settings")
        self.btn_open_sett.setIcon(IconProvider.get_icon("settings", color="#94A3B8", size=14))
        self.btn_open_sett.setIconSize(QSize(14, 14))
        self.btn_open_sett.setProperty("class", "btn-secondary")
        self.btn_open_sett.clicked.connect(self.sig_request_settings.emit)

        self.links_layout.addWidget(self.btn_open_hist)
        self.links_layout.addWidget(self.btn_open_sett)
        left_layout.addLayout(self.links_layout)

        work_layout.addWidget(left_panel)

        # RIGHT COLUMN: Progress Banner, Status Badge, Real-Time Terminal Log
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        # Option B: 5 Side-by-Side Cards (System Ready + 4 StatCards)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)

        # Card 1: System Ready Banner Card
        self.status_banner = QFrame()
        self.status_banner.setObjectName("statusBannerFrame")
        self.status_banner.setFixedHeight(72)
        self.status_banner.minimumSizeHint = lambda: QSize(140, 50)
        self.status_banner.setStyleSheet("""
            QFrame#statusBannerFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        banner_layout = QHBoxLayout(self.status_banner)
        banner_layout.setContentsMargins(12, 6, 12, 6)
        banner_layout.setSpacing(8)

        status_text_box = QVBoxLayout()
        status_text_box.setSpacing(1)
        status_text_box.setAlignment(Qt.AlignVCenter)

        self.lbl_current_stage = QLabel("SYSTEM READY")
        self.lbl_current_stage.setStyleSheet("color: #F8FAFC; font-size: 13px; font-weight: 800; letter-spacing: 0.3px;")
        self.lbl_stage_desc = QLabel("Pilih port & tekan Start Flashing")
        self.lbl_stage_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.lbl_stage_desc.setWordWrap(False)
        status_text_box.addWidget(self.lbl_current_stage)
        status_text_box.addWidget(self.lbl_stage_desc)

        banner_layout.addLayout(status_text_box, stretch=1)

        self.lbl_status_badge = QLabel("READY")
        self.lbl_status_badge.setProperty("class", "badge-ready")
        self.lbl_status_badge.setFixedHeight(26)
        self.lbl_status_badge.setMinimumWidth(72)
        self.lbl_status_badge.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(self.lbl_status_badge)

        cards_row.addWidget(self.status_banner, stretch=5)

        # Cards 2-5: KPI Stat Cards (aligned in exact same row)
        self.card_total = StatCard("TOTAL UNIT", "0", "#F8FAFC")
        self.card_pass = StatCard("PASSED", "0", "#10B981")
        self.card_fail = StatCard("FAILED", "0", "#EF4444")
        self.card_rate = StatCard("PASS RATE", "0.0%", "#38BDF8")

        for card in [self.card_total, self.card_pass, self.card_fail, self.card_rate]:
            card.setFixedHeight(72)
            cards_row.addWidget(card, stretch=2)

        right_panel.addLayout(cards_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - Idle")
        right_panel.addWidget(self.progress_bar)

        # Real-time Terminal Log
        self.terminal = TerminalWidget()
        right_panel.addWidget(self.terminal, stretch=1)

        work_layout.addLayout(right_panel, stretch=1)
        main_layout.addLayout(work_layout, stretch=1)

    def _get_hero_pixmap(self, img_path: Path, target_w: int = 340, target_h: int = 130) -> QPixmap:
        """Loads and auto-frames product hero image with smart content bounding box detection."""
        cache_key = f"{img_path.resolve()}_{target_w}_{target_h}"
        if not hasattr(self, "_hero_cache"):
            self._hero_cache = {}
        if cache_key in self._hero_cache:
            return self._hero_cache[cache_key]

        qimg = QImage(str(img_path))
        w, h = qimg.width(), qimg.height()
        if w == 0 or h == 0:
            pix = QPixmap(str(img_path))
            return pix.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Smart content bounding box detection for studio solid dark backgrounds
        thresh = 12
        top, bottom = 0, h - 1
        left, right = 0, w - 1

        for y in range(0, h, 4):
            if any((qimg.pixelColor(x, y).red() > thresh or qimg.pixelColor(x, y).green() > thresh or qimg.pixelColor(x, y).blue() > thresh) for x in range(0, w, 8)):
                top = max(0, y - 6)
                break

        for y in range(h - 1, 0, -4):
            if any((qimg.pixelColor(x, y).red() > thresh or qimg.pixelColor(x, y).green() > thresh or qimg.pixelColor(x, y).blue() > thresh) for x in range(0, w, 8)):
                bottom = min(h - 1, y + 6)
                break

        for x in range(0, w, 4):
            if any((qimg.pixelColor(x, y).red() > thresh or qimg.pixelColor(x, y).green() > thresh or qimg.pixelColor(x, y).blue() > thresh) for y in range(top, bottom, 8)):
                left = max(0, x - 6)
                break

        for x in range(w - 1, 0, -4):
            if any((qimg.pixelColor(x, y).red() > thresh or qimg.pixelColor(x, y).green() > thresh or qimg.pixelColor(x, y).blue() > thresh) for y in range(top, bottom, 8)):
                right = min(w - 1, x + 6)
                break

        bh = bottom - top
        if bh > 20:
            ratio = target_w / target_h
            pad_y = int(bh * 0.08)
            y0 = max(0, top - pad_y)
            y1 = min(h, bottom + pad_y)
            ch = y1 - y0
            cw = int(ch * ratio)

            cx = (left + right) // 2
            x0 = max(0, cx - cw // 2)
            x1 = min(w, x0 + cw)
            if x1 - x0 < cw and x0 > 0:
                x0 = max(0, x1 - cw)

            cropped = qimg.copy(x0, y0, x1 - x0, y1 - y0)
            scaled = cropped.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pix = QPixmap.fromImage(scaled)
        else:
            pix = QPixmap.fromImage(qimg).scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self._hero_cache[cache_key] = pix
        return pix

    def _update_product_hero_image(self):
        """Updates the product hero banner image according to selected category."""
        category = self.cmb_product.currentData()
        assets_dir = Path(__file__).resolve().parent.parent.parent / "assets"
        
        if category == PRODUCT_CT or "ct" in str(category).lower():
            candidates = [
                assets_dir / "Spart Smart CT.jpg",
                assets_dir / "Sparta Smart CT.jpg",
                assets_dir / "Sparta Smart CT.png",
                assets_dir / "CT.png",
                assets_dir / "CT.jpg",
            ]
        else:
            candidates = [
                assets_dir / "Sparta Smart Plug.jpg",
                assets_dir / "Sparta Smart Plug.png",
                assets_dir / "Plug.png",
                assets_dir / "Plug.jpg",
            ]

        img_path = next((p for p in candidates if p.exists()), candidates[0])

        if img_path.exists():
            pix = self._get_hero_pixmap(img_path, 340, 130)
            self.lbl_hero_img.setPixmap(pix)
        else:
            self.lbl_hero_img.setText(f"[Gambar Produk: {img_path.name}]")
            self.lbl_hero_img.setStyleSheet("color: #64748B; font-size: 11px;")

    def _on_product_changed(self):
        self.custom_firmware_path = None
        self._update_product_hero_image()
        self.update_firmware_status()
        self._check_cloud_updates_silently()

    def _check_cloud_updates_silently(self):
        """Silently queries cloud repository in background to detect firmware updates."""
        category = self.cmb_product.currentData()
        if self.cloud_worker and self.cloud_worker.isRunning():
            return

        self.cloud_worker = CloudSyncWorker(mode="check", product_category=category, parent=self)
        self.cloud_worker.sig_finished.connect(self._on_cloud_check_finished)
        self.cloud_worker.start()

    def _on_cloud_check_finished(self, ok: bool, msg: str, res: dict):
        if not ok:
            self.lbl_cloud_status.setText("○ Cloud OTA: Mode Offline (Cache)")
            self.lbl_cloud_status.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
            self.btn_sync_cloud.setText(" Cek")
            self.btn_sync_cloud.setIcon(IconProvider.get_icon("refresh-cw", "#94A3B8", 12))
            self.btn_sync_cloud.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #94A3B8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #FFFFFF;
                }
            """)
            self.btn_sync_cloud.setEnabled(True)
        elif res.get("has_updates"):
            self.lbl_cloud_status.setText("● Cloud OTA: Update Tersedia!")
            self.lbl_cloud_status.setStyleSheet("color: #FBBF24; font-size: 11px; font-weight: 700;")
            self.btn_sync_cloud.setText(" Unduh")
            self.btn_sync_cloud.setIcon(IconProvider.get_icon("download", "#FFFFFF", 12))
            self.btn_sync_cloud.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    border: 1px solid #F59E0B;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #B45309;
                }
            """)
            self.btn_sync_cloud.setEnabled(True)
        else:
            self.lbl_cloud_status.setText("● Cloud OTA: Terhubung (Terbaru)")
            self.lbl_cloud_status.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 700;")
            self.btn_sync_cloud.setText(" Cek")
            self.btn_sync_cloud.setIcon(IconProvider.get_icon("refresh-cw", "#38BDF8", 12))
            self.btn_sync_cloud.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #38BDF8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    border-color: #38BDF8;
                }
            """)
            self.btn_sync_cloud.setEnabled(True)

    def _on_manual_sync_clicked(self):
        category = self.cmb_product.currentData()
        if self.cloud_worker and self.cloud_worker.isRunning():
            return

        self.btn_sync_cloud.setEnabled(False)
        self.lbl_cloud_status.setText("🔄 Cloud OTA: Sinkronisasi...")
        self.lbl_cloud_status.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 700;")

        self.terminal.append_line(f"[CLOUD OTA] Menghubungkan ke GitHub Pages CDN (https://buildingprocess25.github.io/AlfaEnergyFirmware/firmware/)...")
        self.terminal.append_line(f"[CLOUD OTA] Mengunduh & mengenkripsi biner terbaru untuk {category}...")

        self.cloud_worker = CloudSyncWorker(mode="sync_product", product_category=category, parent=self)
        self.cloud_worker.sig_progress.connect(self._on_cloud_sync_progress)
        self.cloud_worker.sig_finished.connect(self._on_cloud_sync_finished)
        self.cloud_worker.start()

    def _on_cloud_sync_progress(self, pct: int, msg: str):
        self.lbl_cloud_status.setText(f"🔄 Cloud OTA: {pct}%")
        self.terminal.append_line(f"[CLOUD OTA] ({pct}%) {msg}")

    def _on_cloud_sync_finished(self, ok: bool, msg: str, res: dict):
        self.btn_sync_cloud.setEnabled(True)
        if ok:
            self.lbl_cloud_status.setText("● Cloud OTA: Terhubung (Terbaru)")
            self.lbl_cloud_status.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 700;")
            self.btn_sync_cloud.setText(" Cek")
            self.btn_sync_cloud.setIcon(IconProvider.get_icon("refresh-cw", "#38BDF8", 12))
            self.btn_sync_cloud.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #38BDF8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    border-color: #38BDF8;
                }
            """)
            self.terminal.append_line("[CLOUD OTA] ✓ Sukses: Firmware cloud terenkripsi ke dalam local security vault.")
            self.update_firmware_status()
        else:
            self.lbl_cloud_status.setText("✗ Cloud OTA: Gagal Sinkronisasi")
            self.lbl_cloud_status.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 700;")
            self.terminal.append_line(f"[CLOUD OTA] ✗ Gagal: {msg}")

    def _on_port_changed(self):
        idx = self.cmb_ports.currentIndex()
        if idx >= 0:
            port_info: SerialPortInfo = self.cmb_ports.itemData(idx)
            if port_info:
                clean_desc = port_info.description.replace(f"({port_info.device})", "").replace(port_info.device, "").strip(" -:")
                adapter_name = port_info.adapter_chip_type if port_info.adapter_chip_type != "Generic Serial Port" else (clean_desc or "Generic Serial Port")
                if port_info.is_common_esp_adapter:
                    status_text = f"Hardware: {adapter_name}  •  Status: Programmer Siap"
                    self.lbl_port_diag.setText(status_text)
                    self.lbl_port_diag.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 500;")
                else:
                    status_text = f"Hardware: {adapter_name}  •  Baudrate: 921,600 bps"
                    self.lbl_port_diag.setText(status_text)
                    self.lbl_port_diag.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")

    def _auto_scan_ports(self):
        """Silently monitors serial ports in background. Updates dropdown only when changes occur."""
        if self.worker and self.worker.isRunning():
            return
        self.refresh_ports(silent=True)

    def refresh_ports(self, silent: bool = False):
        """Scans COM ports and populates the dropdown smoothly without flicker or resetting active user choice."""
        ports = SerialService.list_ports()

        # Handle empty ports state with no-flicker guard
        if not ports:
            if self.cmb_ports.count() == 1 and self.cmb_ports.itemData(0) is None:
                return
            self.cmb_ports.blockSignals(True)
            self.cmb_ports.clear()
            self.cmb_ports.addItem("No COM Ports Detected", None)
            self.lbl_port_diag.setText("No serial ports found. Connect USB-UART cable and verify drivers.")
            self.lbl_port_diag.setStyleSheet("color: #F87171; font-size: 11px;")
            self.cmb_ports.blockSignals(False)
            self.btn_start.setEnabled(False)
            return

        # Extract currently listed port devices in combobox
        current_devices = []
        for i in range(self.cmb_ports.count()):
            p_data = self.cmb_ports.itemData(i)
            if p_data:
                current_devices.append(p_data.device)

        new_devices = [p.device for p in ports]
        # If port list hasn't changed, skip reload to prevent UI flicker
        if current_devices == new_devices:
            return

        selected_idx = self.cmb_ports.currentIndex()
        selected_dev = self.cmb_ports.itemData(selected_idx).device if (selected_idx >= 0 and self.cmb_ports.itemData(selected_idx)) else None

        self.cmb_ports.blockSignals(True)
        self.cmb_ports.clear()

        new_selected_idx = 0
        newly_added = [p for p in ports if p.device not in current_devices]

        for i, p in enumerate(ports):
            icon_marker = "⚡ " if p.is_common_esp_adapter else "🔌 "
            self.cmb_ports.addItem(f"{icon_marker}{p.display_name}", p)
            if selected_dev and p.device == selected_dev:
                new_selected_idx = i

        # If a new USB cable was just plugged in, auto-select it immediately!
        if newly_added:
            for i, p in enumerate(ports):
                if p.device == newly_added[-1].device:
                    new_selected_idx = i
                    break

        self.cmb_ports.setCurrentIndex(new_selected_idx)
        self.cmb_ports.blockSignals(False)

        if not silent:
            activity_logger.log(
                category=ActivityCategory.HARDWARE,
                action="PORT_SCAN",
                details=f"Detected {len(ports)} serial port(s): {', '.join(p.device for p in ports) if ports else 'None'}",
                status=ActivityStatus.INFO
            )

        self._on_port_changed()
        self._check_can_start()

    def update_firmware_status(self):
        """Auto-binds official firmware binary and verifies target chip requirements."""
        category = self.cmb_product.currentData()
        path = FirmwareService.get_firmware_path(category)
        self.current_firmware_info = FirmwareService.validate_firmware(path, category)

        info = self.current_firmware_info
        config = PRODUCT_CONFIGS.get(category, {})
        target_chip = config.get("target_chip_display") or " / ".join(config.get("supported_chips", []))

        # Mask proprietary firmware filename for corporate IP security
        if "plug" in str(category).lower() or "plug" in str(info.file_name).lower():
            display_fw = "Sparta Smart Plug (Protected)"
        elif "ct" in str(category).lower() or "ct" in str(info.file_name).lower():
            display_fw = "Sparta Smart CT (Protected)"
        else:
            display_fw = f"{config.get('display_name', 'Official System Image')} (Protected)"

        self.lbl_fw_name.setText(display_fw)
        self.lbl_fw_chip.setText(f"{target_chip}  •  Auto-Detect")
        wiring = config.get("wiring_guide", "Power: 3.3V DC | Logic: 3.3V")
        clean_wiring = wiring.replace("Power: ", "").replace("Logic: ", "").replace("|", "•")
        self.lbl_power_spec.setText(clean_wiring)

        # Update firmware source label with metadata
        meta = CloudFirmwareService.load_metadata()
        synced_info = meta.get("files", {}).get(path.name.replace(".alfa_enc", ".bin"))
        if synced_info:
            synced_time = synced_info.get("synced_at", "")[:16].replace("T", " ")
            self.lbl_fw_source.setText(f"Cloud CDN  •  Sync: {synced_time}")
        elif SecurityVault.is_encrypted_vault_file(path):
            self.lbl_fw_source.setText("Security Vault (Terenkripsi)")
        else:
            self.lbl_fw_source.setText("Biner Firmware Lokal (Terenkripsi)")

        if info.exists and info.is_valid:
            self.lbl_fw_hash.setText(f"SHA-256: {info.sha256_hash[:16]}...  (Valid)")
            self.lbl_fw_hash.setStyleSheet("color: #94A3B8; font-size: 10.5px; font-family: 'Consolas', monospace;")
            self.lbl_fw_status.setText("✓ Biner Resmi Terverifikasi")
        else:
            self.lbl_fw_hash.setText("SHA-256: [File Tidak Ditemukan]")
            self.lbl_fw_hash.setStyleSheet("color: #EF4444; font-size: 10.5px; font-family: 'Consolas', monospace;")
            self.lbl_fw_status.setText(f"✗ {info.validation_message}")

        self._check_can_start()

    def update_permissions(self, user=None):
        """Updates quick-link buttons visibility according to role permissions."""
        user = user or auth_service.current_user
        is_restricted_operator = bool(user and not user.is_admin)

        if hasattr(self, "btn_open_hist"):
            self.btn_open_hist.setVisible(not is_restricted_operator)
        if hasattr(self, "btn_open_sett"):
            self.btn_open_sett.setVisible(not is_restricted_operator)

    def _check_can_start(self):
        has_port = self.cmb_ports.count() > 0 and self.cmb_ports.currentData() is not None
        has_firmware = self.current_firmware_info is not None and self.current_firmware_info.is_valid
        
        simulation_active = settings_manager.get("simulation_mode", False)
        # In simulation mode, firmware file is still required or simulation handles it
        can_run = (has_port or simulation_active) and has_firmware
        self.btn_start.setEnabled(can_run)

    def refresh_stats(self):
        """Fetches total pass/fail statistics from database."""
        stats = db_manager.get_statistics()
        self.card_total.set_value(str(stats["total"]))
        self.card_pass.set_value(str(stats["passed"]))
        self.card_fail.set_value(str(stats["failed"]))
        self.card_rate.set_value(f"{stats['pass_rate']}%")

    def start_flashing(self):
        """Initiates the flashing cycle with safety checks."""
        category = self.cmb_product.currentData()
        config = PRODUCT_CONFIGS.get(category, {})

        # Safety & Pre-flight verification dialog check
        require_safety = settings_manager.get("require_safety_acknowledgement", True)
        if require_safety and config.get("requires_ac_isolation_warning", True):
            port_data: Optional[SerialPortInfo] = self.cmb_ports.currentData()
            port_name = port_data.device if port_data else ("MOCK_COM" if settings_manager.get("simulation_mode", False) else "COM?")
            target_chip = config.get("target_chip", "ESP32")

            try:
                dlg = SafetyDialog(
                    product_name=config.get("display_name", category),
                    parent=self,
                    port_name=port_name,
                    firmware_info=self.current_firmware_info,
                    target_chip=target_chip
                )
                if dlg.exec() != SafetyDialog.Accepted:
                    self.terminal.append_line("[SAFETY] Flashing dibatalkan: Operator membatalkan verifikasi pra-flashing.")
                    activity_logger.log(
                        category=ActivityCategory.FLASHING,
                        action="SAFETY_REJECTED",
                        details=f"Operator rejected pre-flight checklist for {category}",
                        status=ActivityStatus.WARNING
                    )
                    return
                activity_logger.log(
                    category=ActivityCategory.FLASHING,
                    action="SAFETY_CONFIRMED",
                    details=f"AC mains safety checklist confirmed for {category} on {port_name}",
                    status=ActivityStatus.INFO
                )
            except Exception as ex:
                self.terminal.append_line(f"[ERROR] Gagal membuka wizard verifikasi: {ex}")
                return

        port_data: Optional[SerialPortInfo] = self.cmb_ports.currentData()
        simulation_active = settings_manager.get("simulation_mode", False)
        
        port_name = port_data.device if port_data else "COM_SIM"
        baudrate = settings_manager.get("default_baudrate", 460800)
        verify_flash = settings_manager.get("verify_flash_write", True)
        erase_all = settings_manager.get("erase_before_flash", True)
        batch_prefix = settings_manager.get("batch_name_prefix", "BATCH-ALFA-")
        if auth_service.is_authenticated:
            operator_name = auth_service.current_user.display_name
            operator_role = auth_service.current_user.role
            op_label = f"Operator: {operator_name} [{operator_role}]"
        else:
            operator_name = settings_manager.get("operator_name", "Operator-1")
            op_label = f"Operator: {operator_name}"

        self.btn_start.setVisible(False)
        self.btn_cancel.setVisible(True)
        self.cmb_product.setEnabled(False)
        self.cmb_ports.setEnabled(False)
        self.btn_refresh_ports.setEnabled(False)

        # Set UI status running
        self.lbl_status_badge.setText("FLASHING")
        self.lbl_status_badge.setProperty("class", "badge-running")
        self.lbl_status_badge.setStyleSheet("")  # refresh stylesheet property
        self.lbl_status_badge.style().unpolish(self.lbl_status_badge)
        self.lbl_status_badge.style().polish(self.lbl_status_badge)

        self.lbl_current_stage.setText("INITIALIZING PIPELINE...")
        self.lbl_current_stage.setStyleSheet("color: #38BDF8; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")
        self.lbl_stage_desc.setText(f"Processing {category} on {port_name}...")
        self.lbl_stage_desc.setToolTip(f"Memproses {category} pada port {port_name}")
        self.progress_bar.setValue(5)
        self.progress_bar.setFormat("%p% - Initializing...")
        self.terminal.clear_log()

        activity_logger.log(
            category=ActivityCategory.FLASHING,
            action="START_FLASH",
            details=f"Target: {category}, Port: {port_name}, Baud: {baudrate}, Erase: {erase_all}, Verify: {verify_flash}",
            status=ActivityStatus.INFO
        )

        # Start worker thread
        self.worker = FlasherWorker(
            product_category=category,
            port=port_name,
            baudrate=baudrate,
            custom_firmware_path=self.custom_firmware_path,
            batch_name=batch_prefix,
            operator_notes=op_label,
            verify_flash=verify_flash,
            erase_all=erase_all,
            simulation_mode=simulation_active,
            parent=self
        )
        self.worker.sig_progress.connect(self._on_worker_progress)
        self.worker.sig_log.connect(self.terminal.append_line)
        self.worker.sig_finished.connect(self._on_worker_finished)
        self.worker.sig_error.connect(self._on_worker_error)
        self.worker.start()

    def cancel_flashing(self):
        """Cancels current flashing worker."""
        if self.worker and self.worker.isRunning():
            self.lbl_stage_desc.setText("Aborting flashing process safely...")
            self.terminal.append_line("[ABORT] Operator requested cancellation...")
            self.worker.cancel()

    def _on_worker_progress(self, percentage: int, stage: str, message: str, is_terminal: bool):
        self.progress_bar.setValue(percentage)
        self.progress_bar.setFormat(f"{percentage}% - {message}")
        clean_msg = message.strip().split('\n')[0][:50]
        self.lbl_stage_desc.setText(clean_msg)
        self.lbl_stage_desc.setToolTip(message)

        if stage == STATUS_ERASING:
            self.lbl_current_stage.setText("ERASING FLASH MEMORY")
            self.lbl_current_stage.setStyleSheet("color: #38BDF8; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")
        elif stage == STATUS_FLASHING:
            self.lbl_current_stage.setText("FLASHING FIRMWARE")
            self.lbl_current_stage.setStyleSheet("color: #38BDF8; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")
        elif stage == STATUS_VERIFYING:
            self.lbl_current_stage.setText("VERIFYING CHECKSUM")
            self.lbl_current_stage.setStyleSheet("color: #38BDF8; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")

    def _on_worker_finished(self, record: ProductionRecord):
        self._reset_controls()
        self.refresh_stats()

        if record.result == STATUS_PASS:
            sound_service.play_success()
            self.lbl_status_badge.setText("PASS")
            self.lbl_status_badge.setProperty("class", "badge-pass")
            self.lbl_current_stage.setText("FLASHING SUCCESSFUL")
            self.lbl_current_stage.setStyleSheet("color: #34D399; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")
            self.lbl_stage_desc.setText(
                f"MAC: {record.mac_address or 'N/A'} • Chip: {record.target_chip} • {record.duration_seconds}s"
            )
            self.lbl_stage_desc.setToolTip(
                f"Perangkat: {getattr(record, 'product_name', None) or getattr(record, 'product_category', 'Device')}\nMAC: {record.mac_address or 'N/A'}\nChip: {record.target_chip}\nWaktu: {record.duration_seconds}s\nStatus: Otomatis terdaftar ke Device Monitor"
            )
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("100% - PASS")
            activity_logger.log(
                category=ActivityCategory.FLASHING,
                action="FLASH_PASS",
                details=f"Device MAC: {record.mac_address or 'N/A'}, Product: {getattr(record, 'product_name', None) or getattr(record, 'product_category', 'Device')}, Chip: {record.target_chip}, Duration: {record.duration_seconds}s",
                status=ActivityStatus.SUCCESS
            )

        elif record.result == STATUS_CANCELLED:
            sound_service.play_warning()
            self.lbl_status_badge.setText("CANCEL")
            self.lbl_status_badge.setProperty("class", "badge-warn")
            self.lbl_current_stage.setText("FLASHING CANCELLED")
            self.lbl_current_stage.setStyleSheet("color: #FBBF24; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")
            self.lbl_stage_desc.setText("Proses dibatalkan oleh operator.")
            self.lbl_stage_desc.setToolTip("")
            self.progress_bar.setFormat("Cancelled")
            activity_logger.log(
                category=ActivityCategory.FLASHING,
                action="FLASH_CANCELLED",
                details=f"Flashing aborted by operator for {getattr(record, 'product_name', None) or getattr(record, 'product_category', 'Device')}",
                status=ActivityStatus.WARNING
            )
        else:
            sound_service.play_failure()
            self.lbl_status_badge.setText("FAIL")
            self.lbl_status_badge.setProperty("class", "badge-fail")
            self.lbl_current_stage.setText("FLASHING FAILED")
            self.lbl_current_stage.setStyleSheet("color: #F87171; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")
            
            raw_err = (record.error_message or "Unknown error").strip()
            first_line = raw_err.split('\n')[0].replace("A fatal error occurred: ", "").replace("Error: ", "").strip()
            if len(first_line) > 46:
                first_line = first_line[:43] + "..."
            port_suffix = f" ({record.serial_port})" if record.serial_port else ""
            self.lbl_stage_desc.setText(f"Error: {first_line}{port_suffix}")
            self.lbl_stage_desc.setToolTip(raw_err)
            self.progress_bar.setFormat("FAIL")
            activity_logger.log(
                category=ActivityCategory.FLASHING,
                action="FLASH_FAIL",
                details=f"Failed flashing {getattr(record, 'product_name', None) or getattr(record, 'product_category', 'Device')}: {record.error_message or 'Unknown error'}",
                status=ActivityStatus.ERROR
            )

        self.lbl_status_badge.style().unpolish(self.lbl_status_badge)
        self.lbl_status_badge.style().polish(self.lbl_status_badge)

    def _on_worker_error(self, err_msg: str):
        sound_service.play_failure()
        self._reset_controls()
        self.refresh_stats()
        self.lbl_status_badge.setText("FAIL")
        self.lbl_status_badge.setProperty("class", "badge-fail")
        self.lbl_status_badge.style().unpolish(self.lbl_status_badge)
        self.lbl_status_badge.style().polish(self.lbl_status_badge)
        self.lbl_current_stage.setText("FLASHING FAILED")
        self.lbl_current_stage.setStyleSheet("color: #F87171; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")
        clean_err = err_msg.strip().split('\n')[0][:46]
        self.lbl_stage_desc.setText(f"Error: {clean_err}")
        self.lbl_stage_desc.setToolTip(err_msg)
        self.terminal.append_line(f"[CRITICAL WORKER ERROR] {err_msg}")
        QMessageBox.critical(self, "Flashing Error", f"Unexpected worker error:\n{err_msg}")

    def _reset_controls(self):
        self.btn_start.setVisible(True)
        self.btn_cancel.setVisible(False)
        self.cmb_product.setEnabled(True)
        self.cmb_ports.setEnabled(True)
        self.btn_refresh_ports.setEnabled(True)
        self.worker = None

