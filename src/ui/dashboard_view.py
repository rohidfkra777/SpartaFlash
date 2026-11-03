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
from PySide6.QtCore import Qt, Signal, QSize

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
        self.refresh_ports()
        self.update_firmware_status()
        self.refresh_stats()
        self._check_cloud_updates_silently()
        # Automated zero-touch USB driver check & installation
        DriverService.auto_ensure_drivers_installed(callback_on_installed=self.refresh_ports)
        self.update_permissions()
        auth_service.sig_auth_state_changed.connect(self.update_permissions)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Bar: Title & Production KPI Summary
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_dash_title = QLabel("PRODUCTION WORKSTATION")
        lbl_dash_title.setStyleSheet("color: #38BDF8; font-size: 20px; font-weight: 800; letter-spacing: 0.5px;")
        lbl_dash_sub = QLabel("Automated Firmware Flashing & Hardware Verification Pipeline")
        lbl_dash_sub.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        title_box.addWidget(lbl_dash_title)
        title_box.addWidget(lbl_dash_sub)

        top_layout.addLayout(title_box)
        top_layout.addStretch()

        # KPI Stat Cards
        self.card_total = StatCard("Total Units", "0", "#F8FAFC")
        self.card_pass = StatCard("Passed (PASS)", "0", "#10B981")
        self.card_fail = StatCard("Failed (FAIL)", "0", "#EF4444")
        self.card_rate = StatCard("Pass Rate", "0.0%", "#38BDF8")

        for card in [self.card_total, self.card_pass, self.card_fail, self.card_rate]:
            card.setMinimumWidth(125)
            top_layout.addWidget(card)

        main_layout.addLayout(top_layout)

        # 2. Main Work Area: Left Control Panel (Settings & Firmware), Right Terminal & Status
        work_layout = QHBoxLayout()
        work_layout.setSpacing(16)

        # LEFT COLUMN: Configuration, Port, Firmware, Start Action
        left_panel = QFrame()
        left_panel.setProperty("class", "card")
        left_panel.setFixedWidth(400)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        # A. Section 1: TARGET PRODUK PRODUKSI (AUTO-LOCKED)
        sec_prod_header = QHBoxLayout()
        lbl_sec_prod = QLabel("1. TARGET PRODUK PRODUKSI")
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

        self.cmb_product.addItem(icon_plug, "  AlfaEnergy Smart Plug (Plug)", PRODUCT_PLUG)
        self.cmb_product.addItem(icon_ct, "  AlfaEnergy Current Transformer (CT)", PRODUCT_CT)
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

        # Profile Auto-Lock Box (Zero-Config Firmware & Target Binding)
        self.frame_fw = QFrame()
        self.frame_fw.setObjectName("frameFwAutoLock")
        self.frame_fw.setStyleSheet("""
            QFrame#frameFwAutoLock {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        fw_box = QVBoxLayout(self.frame_fw)
        fw_box.setSpacing(4)
        fw_box.setContentsMargins(10, 8, 10, 8)

        lbl_autolock_header = QLabel("🔒 PROFIL RESMI TERKUNCI (AUTO-BINDING)")
        lbl_autolock_header.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 800; letter-spacing: 0.3px;")
        fw_box.addWidget(lbl_autolock_header)

        self.lbl_fw_name = QLabel("Firmware: Memuat...")
        self.lbl_fw_name.setWordWrap(True)
        self.lbl_fw_name.setStyleSheet("color: #F8FAFC; font-weight: 700; font-size: 12px;")

        self.lbl_fw_chip = QLabel("Target Chip: -")
        self.lbl_fw_chip.setWordWrap(True)
        self.lbl_fw_chip.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 600;")
        
        self.lbl_fw_hash = QLabel("SHA-256: -")
        self.lbl_fw_hash.setWordWrap(True)
        self.lbl_fw_hash.setStyleSheet("color: #94A3B8; font-size: 10.5px; font-family: monospace;")
        
        self.lbl_fw_source = QLabel("Sumber: Cloud CDN (GitHub Pages)")
        self.lbl_fw_source.setWordWrap(True)
        self.lbl_fw_source.setStyleSheet("color: #38BDF8; font-size: 10.5px; font-weight: 600;")

        self.lbl_fw_status = QLabel("Status: -")
        self.lbl_fw_status.setWordWrap(True)
        self.lbl_power_spec = QLabel("Spesifikasi Daya: -")
        self.lbl_power_spec.setWordWrap(True)
        self.lbl_power_spec.setStyleSheet("color: #FCD34D; font-size: 11px; font-weight: 700;")

        fw_box.addWidget(self.lbl_fw_name)
        fw_box.addWidget(self.lbl_fw_chip)
        fw_box.addWidget(self.lbl_power_spec)
        fw_box.addWidget(self.lbl_fw_hash)
        fw_box.addWidget(self.lbl_fw_source)
        fw_box.addWidget(self.lbl_fw_status)

        left_layout.addWidget(self.frame_fw)
        left_layout.addSpacing(4)

        # B. Section 2: SERIAL PORT & FLASHING
        lbl_sec_port = QLabel("2. KONEKSI USB & FLASHING")
        lbl_sec_port.setProperty("class", "card-title")
        left_layout.addWidget(lbl_sec_port)

        port_ctrl_layout = QHBoxLayout()
        self.cmb_ports = QComboBox()
        self.cmb_ports.currentIndexChanged.connect(self._on_port_changed)

        self.btn_refresh_ports = QPushButton(" Scan Port")
        self.btn_refresh_ports.setIcon(IconProvider.get_icon("refresh-cw", color="#38BDF8", size=14))
        self.btn_refresh_ports.setIconSize(QSize(14, 14))
        self.btn_refresh_ports.setProperty("class", "btn-secondary")
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)

        port_ctrl_layout.addWidget(self.cmb_ports, stretch=1)
        port_ctrl_layout.addWidget(self.btn_refresh_ports)
        left_layout.addLayout(port_ctrl_layout)

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

        # Big Visual Status Banner
        self.status_banner = QFrame()
        self.status_banner.setObjectName("statusBannerFrame")
        self.status_banner.setStyleSheet("""
            QFrame#statusBannerFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        banner_layout = QHBoxLayout(self.status_banner)
        banner_layout.setContentsMargins(16, 12, 16, 12)

        status_text_box = QVBoxLayout()
        self.lbl_current_stage = QLabel("SYSTEM READY")
        self.lbl_current_stage.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 700; letter-spacing: 0.3px;")
        self.lbl_stage_desc = QLabel("Select port, verify firmware, and press Start Flashing.")
        self.lbl_stage_desc.setWordWrap(True)
        self.lbl_stage_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        status_text_box.addWidget(self.lbl_current_stage)
        status_text_box.addWidget(self.lbl_stage_desc)

        banner_layout.addLayout(status_text_box)
        banner_layout.addStretch()

        self.lbl_status_badge = QLabel("READY")
        self.lbl_status_badge.setProperty("class", "badge-ready")
        self.lbl_status_badge.setMinimumWidth(110)
        self.lbl_status_badge.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(self.lbl_status_badge)

        right_panel.addWidget(self.status_banner)

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

    def _on_product_changed(self):
        self.custom_firmware_path = None
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
                diag = f"Device: {port_info.device} ({port_info.description})\nAdapter: {port_info.adapter_chip_type}"
                if port_info.is_common_esp_adapter:
                    diag += " [Verified ESP Programmer Adapter]"
                self.lbl_port_diag.setText(diag)
                self.lbl_port_diag.setStyleSheet("color: #38BDF8; font-size: 11px;")

    def refresh_ports(self):
        """Scans COM ports and populates the dropdown."""
        self.cmb_ports.clear()
        ports = SerialService.list_ports()
        if not ports:
            self.cmb_ports.addItem("No COM Ports Detected", None)
            self.lbl_port_diag.setText("No serial ports found. Connect USB-UART cable and verify drivers.")
            self.lbl_port_diag.setStyleSheet("color: #F87171; font-size: 11px;")
            self.btn_start.setEnabled(False)
            return

        for p in ports:
            icon_marker = "⚡ " if p.is_common_esp_adapter else "🔌 "
            self.cmb_ports.addItem(f"{icon_marker}{p.display_name}", p)

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
            display_fw = "Alfa Smart Plug (Protected)"
        elif "ct" in str(category).lower() or "ct" in str(info.file_name).lower():
            display_fw = "Alfa Energy CT (Protected)"
        else:
            display_fw = f"{config.get('display_name', 'Official System Image')} (Protected)"

        self.lbl_fw_name.setText(f"Firmware: {display_fw}")
        self.lbl_fw_chip.setText(f"Target Chip: {target_chip} (Validasi Otomatis)")
        wiring = config.get("wiring_guide", "Power: 3.3V DC | Logic: 3.3V")
        self.lbl_power_spec.setText(f"⚡ {wiring}")

        # Update firmware source label with metadata
        meta = CloudFirmwareService.load_metadata()
        synced_info = meta.get("files", {}).get(path.name.replace(".alfa_enc", ".bin"))
        if synced_info:
            synced_time = synced_info.get("synced_at", "")[:16].replace("T", " ")
            self.lbl_fw_source.setText(f"🌐 Cloud CDN (Terenkripsi • Sync: {synced_time})")
        elif SecurityVault.is_encrypted_vault_file(path):
            self.lbl_fw_source.setText("🌐 Security Vault (.alfa_enc Terenkripsi)")
        else:
            self.lbl_fw_source.setText("📁 Biner Firmware Lokal")

        if info.exists and info.is_valid:
            self.lbl_fw_hash.setText(f"SHA-256: {info.sha256_hash[:18]}... (Valid)")
            self.lbl_fw_status.setText("✓ Biner Resmi Terverifikasi")
            self.lbl_fw_status.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 700;")
        else:
            self.lbl_fw_hash.setText("SHA-256: [File Tidak Ditemukan]")
            self.lbl_fw_status.setText(f"✗ {info.validation_message}")
            self.lbl_fw_status.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 700;")

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
        self.lbl_stage_desc.setText(f"Processing {category} on {port_name}...")
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
        self.lbl_stage_desc.setText(message)

        if stage == STATUS_ERASING:
            self.lbl_current_stage.setText("ERASING FLASH MEMORY")
        elif stage == STATUS_FLASHING:
            self.lbl_current_stage.setText("FLASHING FIRMWARE")
        elif stage == STATUS_VERIFYING:
            self.lbl_current_stage.setText("VERIFYING CHECKSUM")

    def _on_worker_finished(self, record: ProductionRecord):
        self._reset_controls()
        self.refresh_stats()

        if record.result == STATUS_PASS:
            sound_service.play_success()
            self.lbl_status_badge.setText("PASS")
            self.lbl_status_badge.setProperty("class", "badge-pass")
            self.lbl_current_stage.setText("FLASHING SUCCESSFUL (PASS)")
            self.lbl_stage_desc.setText(
                f"Device MAC: {record.mac_address or 'N/A'} | Chip: {record.target_chip} | Time: {record.duration_seconds}s | Auto-registered to Device Monitor"
            )
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("100% - PASS")
            activity_logger.log(
                category=ActivityCategory.FLASHING,
                action="FLASH_PASS",
                details=f"Device MAC: {record.mac_address or 'N/A'}, Product: {record.product_name}, Chip: {record.target_chip}, Duration: {record.duration_seconds}s",
                status=ActivityStatus.SUCCESS
            )

        elif record.result == STATUS_CANCELLED:
            sound_service.play_warning()
            self.lbl_status_badge.setText("CANCELLED")
            self.lbl_status_badge.setProperty("class", "badge-warn")
            self.lbl_current_stage.setText("FLASHING CANCELLED")
            self.lbl_stage_desc.setText("Process was aborted by operator.")
            self.progress_bar.setFormat("Cancelled")
            activity_logger.log(
                category=ActivityCategory.FLASHING,
                action="FLASH_CANCELLED",
                details=f"Flashing aborted by operator for {record.product_name}",
                status=ActivityStatus.WARNING
            )
        else:
            sound_service.play_failure()
            self.lbl_status_badge.setText("FAIL")
            self.lbl_status_badge.setProperty("class", "badge-fail")
            self.lbl_current_stage.setText("FLASHING FAILED (FAIL)")
            self.lbl_stage_desc.setText(f"Error: {record.error_message or 'Unknown error'}")
            self.progress_bar.setFormat("FAIL")
            activity_logger.log(
                category=ActivityCategory.FLASHING,
                action="FLASH_FAIL",
                details=f"Failed flashing {record.product_name}: {record.error_message or 'Unknown error'}",
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
        self.terminal.append_line(f"[CRITICAL WORKER ERROR] {err_msg}")
        QMessageBox.critical(self, "Flashing Error", f"Unexpected worker error:\n{err_msg}")

    def _reset_controls(self):
        self.btn_start.setVisible(True)
        self.btn_cancel.setVisible(False)
        self.cmb_product.setEnabled(True)
        self.cmb_ports.setEnabled(True)
        self.btn_refresh_ports.setEnabled(True)
        self.worker = None

