"""
SpartaFlash - Settings & Hardware Diagnostics View.
Developer: Rohidfkra777
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit,
    QCheckBox, QFrame, QMessageBox, QTextEdit
)
from src.config.constants import BAUD_RATES
from src.config.settings import settings_manager
from src.services.sound_service import sound_service
from src.services.dependency_service import DependencyService
from src.ui.components.icon_provider import IconProvider
from src.services.auth_service import auth_service

class SettingsView(QWidget):
    """Configuration workstation for flashing parameters, safety rules, and dependencies."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_values()
        auth_service.sig_auth_state_changed.connect(lambda _: self.load_values())

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Header
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title_box.setContentsMargins(0, 0, 0, 0)
        lbl_title = QLabel("STATION CONFIGURATION & DIAGNOSTICS")
        lbl_title.setStyleSheet("color: #38BDF8; font-size: 18px; font-weight: 800; letter-spacing: 0.8px; font-family: 'Segoe UI', -apple-system, sans-serif;")
        lbl_sub = QLabel("Flashing parameters, safety protocols, operator metadata, and runtime dependencies")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 11.5px; font-weight: 500; font-family: 'Segoe UI', -apple-system, sans-serif;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        main_layout.addLayout(title_box)

        # Main Layout Grid / Split
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(16)

        # LEFT CARD: Flashing & Production Parameters
        left_card = QFrame()
        left_card.setProperty("class", "card")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        lbl_sec1 = QLabel("FLASHING PARAMETERS")
        lbl_sec1.setProperty("class", "card-title")
        left_layout.addWidget(lbl_sec1)

        # Baudrate
        lbl_baud = QLabel("Flashing Baud Rate:")
        lbl_baud.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 600;")
        self.cmb_baud = QComboBox()
        for b in BAUD_RATES:
            self.cmb_baud.addItem(f"{b} bps (Recommended)" if b == 460800 else f"{b} bps", b)
        left_layout.addWidget(lbl_baud)
        left_layout.addWidget(self.cmb_baud)

        # Checkboxes
        self.chk_erase = QCheckBox("Erase Entire Flash Memory Prior to Flashing (--erase-all)")
        self.chk_erase.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 700;")
        left_layout.addWidget(self.chk_erase)

        self.chk_verify = QCheckBox("Verify Flash Memory Post-Write (--verify)")
        self.chk_verify.setStyleSheet("color: #F8FAFC; font-size: 12px;")
        left_layout.addWidget(self.chk_verify)

        self.chk_safety = QCheckBox("Enforce Mandatory High-Voltage AC Safety Checklist")
        self.chk_safety.setStyleSheet("color: #F8FAFC; font-size: 12px;")
        left_layout.addWidget(self.chk_safety)

        # Audio Alert Settings
        sound_box = QHBoxLayout()
        self.chk_sound = QCheckBox("Enable Audio Alerts (Beep Sound on Pass / Fail)")
        self.chk_sound.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 700;")
        self.btn_test_sound = QPushButton("🔊 Test Audio Beep")
        self.btn_test_sound.setFixedHeight(26)
        self.btn_test_sound.setStyleSheet("background-color: #1E293B; color: #38BDF8; border: 1px solid #38BDF8; border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: 600;")
        self.btn_test_sound.clicked.connect(lambda: sound_service.play_success(force=True))
        sound_box.addWidget(self.chk_sound)
        sound_box.addStretch()
        sound_box.addWidget(self.btn_test_sound)
        left_layout.addLayout(sound_box)

        # Production Metadata
        lbl_sec2 = QLabel("OPERATOR & BATCH METADATA")
        lbl_sec2.setProperty("class", "card-title")
        left_layout.addWidget(lbl_sec2)

        lbl_op = QLabel("Station Operator ID / Name:")
        lbl_op.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 600;")
        self.txt_operator = QLineEdit()
        left_layout.addWidget(lbl_op)
        left_layout.addWidget(self.txt_operator)

        lbl_batch_prefix = QLabel("Batch ID Prefix:")
        lbl_batch_prefix.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 600;")
        self.txt_batch_prefix = QLineEdit()
        left_layout.addWidget(lbl_batch_prefix)
        left_layout.addWidget(self.txt_batch_prefix)

        # Testing & Simulation Mode
        lbl_sec3 = QLabel("TESTING & SIMULATION (OFFLINE QA)")
        lbl_sec3.setProperty("class", "card-title")
        left_layout.addWidget(lbl_sec3)

        self.chk_simulation = QCheckBox("Enable Hardware Simulation Mode (Mock Flashing)")
        self.chk_simulation.setStyleSheet("color: #FBBF24; font-size: 12px; font-weight: 700;")
        left_layout.addWidget(self.chk_simulation)

        lbl_sim_desc = QLabel("Allows end-to-end software testing and verification without physical ESP device attached.")
        lbl_sim_desc.setWordWrap(True)
        lbl_sim_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        left_layout.addWidget(lbl_sim_desc)

        left_layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        self.btn_save = QPushButton(" Save Settings")
        self.btn_save.setIcon(IconProvider.get_icon("save", "#FFFFFF", 16))
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self.save_values)

        self.btn_reset = QPushButton(" Reset Defaults")
        self.btn_reset.setIcon(IconProvider.get_icon("rotate-ccw", "#94A3B8", 16))
        self.btn_reset.setProperty("class", "btn-secondary")
        self.btn_reset.clicked.connect(self.reset_defaults)

        btn_box.addWidget(self.btn_reset)
        btn_box.addWidget(self.btn_save)
        left_layout.addLayout(btn_box)

        grid_layout.addWidget(left_card, stretch=1)

        # RIGHT CARD: Dependency Diagnostics
        right_card = QFrame()
        right_card.setProperty("class", "card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        lbl_sec_dep = QLabel("TOOLCHAIN & DEPENDENCY INTEGRITY")
        lbl_sec_dep.setProperty("class", "card-title")
        right_layout.addWidget(lbl_sec_dep)

        self.txt_diag = QTextEdit()
        self.txt_diag.setReadOnly(True)
        self.txt_diag.setStyleSheet("""
            QTextEdit {
                background-color: #090D16;
                color: #38BDF8;
                border: 1px solid #1E293B;
                border-radius: 8px;
                font-family: 'Cascadia Mono', 'Consolas', monospace;
                font-size: 12px;
                padding: 12px;
            }
        """)
        right_layout.addWidget(self.txt_diag, stretch=1)

        btn_check_deps = QPushButton(" Re-check System Dependencies")
        btn_check_deps.setIcon(IconProvider.get_icon("wrench", "#94A3B8", 14))
        btn_check_deps.setProperty("class", "btn-secondary")
        btn_check_deps.clicked.connect(self.run_dependency_check)
        right_layout.addWidget(btn_check_deps)

        grid_layout.addWidget(right_card, stretch=1)
        main_layout.addLayout(grid_layout, stretch=1)

        self.run_dependency_check()

    def load_values(self):
        baud = settings_manager.get("default_baudrate", 460800)
        idx = self.cmb_baud.findData(baud)
        if idx >= 0:
            self.cmb_baud.setCurrentIndex(idx)

        self.chk_erase.setChecked(settings_manager.get("erase_before_flash", True))
        self.chk_verify.setChecked(settings_manager.get("verify_flash_write", True))
        self.chk_safety.setChecked(settings_manager.get("require_safety_acknowledgement", True))
        self.chk_sound.setChecked(settings_manager.get("play_sound_on_completion", True))

        if auth_service.is_authenticated:
            user = auth_service.current_user
            self.txt_operator.setText(f"{user.display_name} ({user.role})")
            self.txt_operator.setReadOnly(True)
            self.txt_operator.setToolTip(f"Locked to active authenticated account: {user.username}")
        else:
            self.txt_operator.setText(settings_manager.get("operator_name", "Operator-1"))
            self.txt_operator.setReadOnly(False)

        self.txt_batch_prefix.setText(settings_manager.get("batch_name_prefix", "BATCH-ALFA-"))

        # Role-based simulation control
        is_admin = auth_service.is_admin
        self.chk_simulation.setEnabled(is_admin)
        if is_admin:
            self.chk_simulation.setText("Enable Hardware Simulation Mode (Mock Flashing)")
            self.chk_simulation.setChecked(settings_manager.get("simulation_mode", False))
        else:
            self.chk_simulation.setText("Enable Hardware Simulation Mode (Mock Flashing)")
            self.chk_simulation.setChecked(False)

    def save_values(self):
        baud = self.cmb_baud.currentData()
        settings_manager.set("default_baudrate", baud)
        settings_manager.set("erase_before_flash", self.chk_erase.isChecked())
        settings_manager.set("verify_flash_write", self.chk_verify.isChecked())
        settings_manager.set("require_safety_acknowledgement", self.chk_safety.isChecked())
        settings_manager.set("play_sound_on_completion", self.chk_sound.isChecked())

        if auth_service.is_authenticated:
            settings_manager.set("operator_name", auth_service.current_user.display_name)
        else:
            settings_manager.set("operator_name", self.txt_operator.text().strip() or "Operator-1")

        settings_manager.set("batch_name_prefix", self.txt_batch_prefix.text().strip() or "BATCH-ALFA-")

        # Only Administrator can persist simulation mode
        if auth_service.is_admin:
            settings_manager.set("simulation_mode", self.chk_simulation.isChecked())
        else:
            settings_manager.set("simulation_mode", False)

        settings_manager.save()
        QMessageBox.information(self, "Settings Saved", "Application settings successfully saved.")

    def reset_defaults(self):
        from src.config.settings import DEFAULT_SETTINGS
        settings_manager.settings = DEFAULT_SETTINGS.copy()
        settings_manager.save()
        self.load_values()
        QMessageBox.information(self, "Reset", "Settings reset to defaults.")

    def run_dependency_check(self):
        res = DependencyService.check_all_dependencies()
        lines = [
            "==================================================",
            "        SYSTEM DEPENDENCY INTEGRITY CHECK         ",
            "==================================================",
            f"Python Runtime   : {res['python_version']}",
            f"Python Binary    : {res['executable']}",
            f"All Required Met : {'YES (PASSED)' if res['all_required_met'] else 'NO (MISSING REQUIRED)'}",
            "--------------------------------------------------"
        ]
        for dep in res["dependencies"]:
            status_str = f"INSTALLED (v{dep.version})" if dep.is_installed else "NOT INSTALLED"
            req_str = "REQUIRED" if dep.required else "OPTIONAL"
            lines.append(f"• [{req_str}] {dep.name:<14}: {status_str}")
            lines.append(f"    Info : {dep.description}")
            if not dep.is_installed:
                lines.append(f"    Fix  : {dep.install_guide}")
            lines.append("")

        lines.append("==================================================")
        self.txt_diag.setText("\n".join(lines))
