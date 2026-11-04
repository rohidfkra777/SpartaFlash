"""
SpartaFlash - Main Application Window.
Developer: Rohidfkra777
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QSplitter
)
from PySide6.QtCore import Qt, QUrl, QSize, QPoint, QTimer
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap

from src.config.constants import (
    APP_NAME, APP_VERSION, DEVELOPER_NAME, DEVELOPER_GITHUB,
    COPYRIGHT_NOTICE, DEVELOPER_FOOTER_TEXT, APP_ICON_PATH, LOGO_HORIZONTAL_PATH,
    ORGANIZATION_NAME, ORGANIZATION_DEPT
)
from src.ui.styles import INDUSTRIAL_DARK_QSS
from src.ui.dashboard_view import DashboardView
from src.ui.mqtt_monitor_view import MqttMonitorView
from src.ui.history_view import HistoryView
from src.ui.activity_log_view import ActivityLogView
from src.ui.settings_view import SettingsView
from src.ui.about_view import AboutView
from src.ui.components.icon_provider import IconProvider
from src.services.auth_service import auth_service
from src.ui.components.login_dialog import LoginDialog
from src.ui.components.change_password_dialog import ChangePasswordDialog
from src.ui.components.add_user_dialog import AddUserDialog
from src.ui.components.user_management_dialog import UserManagementDialog

class MainWindow(QMainWindow):
    """Main window hosting navigation sidebar, view stack, and developer attribution footer."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - Production Workstation")
        self.resize(1180, 750)
        self.setMinimumSize(960, 620)
        self.setStyleSheet(INDUSTRIAL_DARK_QSS)
        self.last_sidebar_width = 230
        self.is_rail_mode = False
        self.NAV_ITEMS = [
            {"icon_name": "zap", "title": "Flash Station", "tooltip": "Firmware Flashing Workstation"},
            {"icon_name": "radio", "title": "Device Monitor", "tooltip": "Live MQTT Device Telemetry & Control"},
            {"icon_name": "history", "title": "Production History", "tooltip": "Production History Log"},
            {"icon_name": "activity", "title": "Activity Logs", "tooltip": "User Activity & Operational Audit Log"},
            {"icon_name": "settings", "title": "Station Settings", "tooltip": "Station Configuration & Diagnostics"},
            {"icon_name": "info", "title": "About System", "tooltip": "System Information & Attribution"},
        ]
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        self._init_ui()
        self._update_user_ui()
        auth_service.sig_auth_state_changed.connect(self._update_user_ui)



    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Body Splitter: Resizable & Collapsible Sidebar + Content Container
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("mainSplitter")

        # Sidebar Frame (Supports 64px Compact Rail Mode up to 400px Expanded)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebarFrame")
        self.sidebar.setMinimumWidth(64)
        self.sidebar.setMaximumWidth(400)
        self.side_layout = QVBoxLayout(self.sidebar)
        self.side_layout.setContentsMargins(8, 14, 8, 14)
        self.side_layout.setSpacing(8)

        # Header 1: Expanded Mode (Full Brand Logo + '◀' Collapse to Rail)
        self.header_expanded = QWidget()
        header_exp_layout = QHBoxLayout(self.header_expanded)
        header_exp_layout.setContentsMargins(0, 0, 0, 0)
        header_exp_layout.setSpacing(6)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(4)
        if LOGO_HORIZONTAL_PATH.exists():
            lbl_logo_img = QLabel()
            pix = QPixmap(str(LOGO_HORIZONTAL_PATH)).scaledToWidth(175, Qt.SmoothTransformation)
            lbl_logo_img.setPixmap(pix)
            brand_box.addWidget(lbl_logo_img)
        else:
            lbl_logo = QLabel("⚡ SPARTAFLASH")
            lbl_logo.setObjectName("appTitleLabel")
            lbl_subtitle = QLabel("STRIKE FAST. FLASH TRUE.")
            lbl_subtitle.setObjectName("appSubtitleLabel")
            brand_box.addWidget(lbl_logo)
            brand_box.addWidget(lbl_subtitle)
        header_exp_layout.addLayout(brand_box, stretch=1)



        # Header 2: Compact Rail Mode (Clean Brand Mini Logo - Clickable to Expand)
        self.header_rail = QWidget()
        header_rail_layout = QVBoxLayout(self.header_rail)
        header_rail_layout.setContentsMargins(0, 0, 0, 0)
        header_rail_layout.setSpacing(6)

        if APP_ICON_PATH.exists():
            lbl_mini_logo = QLabel()
            pix_mini = QPixmap(str(APP_ICON_PATH)).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_mini_logo.setPixmap(pix_mini)
        else:
            lbl_mini_logo = QLabel("⚡")
            lbl_mini_logo.setObjectName("miniLogoLabel")
        lbl_mini_logo.setAlignment(Qt.AlignCenter)
        lbl_mini_logo.setCursor(Qt.PointingHandCursor)
        lbl_mini_logo.setToolTip(f"{APP_NAME} (Klik untuk buka sidebar)")
        lbl_mini_logo.mousePressEvent = lambda _: self.toggle_sidebar_rail()

        header_rail_layout.addWidget(lbl_mini_logo, alignment=Qt.AlignCenter)

        self.side_layout.addWidget(self.header_expanded)
        self.side_layout.addWidget(self.header_rail)
        self.header_rail.setVisible(False)

        self.side_layout.addSpacing(6)

        # Nav Buttons with Operations / Configuration Divider
        self.nav_buttons = []
        for i, item in enumerate(self.NAV_ITEMS):


            btn = QPushButton(f"  {item['title']}")
            btn.setIcon(IconProvider.get_icon(item["icon_name"], color="#94A3B8", active_color="#38BDF8", size=18))
            btn.setIconSize(QSize(18, 18))
            btn.setProperty("class", "nav-button")
            btn.setProperty("compact", "false")
            btn.setFixedHeight(38)
            btn.setCheckable(True)
            btn.setToolTip(item["tooltip"])
            btn.clicked.connect(lambda _, idx=i: self.switch_view(idx))
            self.side_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        self.side_layout.addStretch()

        # Authenticated Session User Card
        self.user_card = QFrame()
        self.user_card.setObjectName("userSessionCard")
        self.user_card.setStyleSheet("""
            QFrame#userSessionCard {
                background-color: #0B1120;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        user_card_layout = QVBoxLayout(self.user_card)
        user_card_layout.setContentsMargins(8, 6, 8, 6)
        user_card_layout.setSpacing(4)

        user_top = QHBoxLayout()
        user_top.setSpacing(4)

        self.lbl_user_role = QLabel("ADMIN")
        self.lbl_user_role.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1);
            color: #FFFFFF;
            font-size: 9px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        user_top.addWidget(self.lbl_user_role)
        user_top.addStretch()

        self.btn_manage_users = QPushButton("")
        self.btn_manage_users.setIcon(IconProvider.get_icon("users", "#38BDF8", 12))
        self.btn_manage_users.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38BDF8;
            }
        """)
        self.btn_manage_users.setToolTip("Kelola Akun Operator (Lihat, Tambah, Hapus)")
        self.btn_manage_users.clicked.connect(self._on_manage_users)
        user_top.addWidget(self.btn_manage_users)

        self.btn_change_pass = QPushButton("")
        self.btn_change_pass.setIcon(IconProvider.get_icon("key", "#FCD34D", 12))
        self.btn_change_pass.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #FCD34D;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #FCD34D;
            }
        """)
        self.btn_change_pass.setToolTip("Ganti Password Akun")
        self.btn_change_pass.clicked.connect(self._on_change_password)
        user_top.addWidget(self.btn_change_pass)

        self.btn_lock_station = QPushButton("Lock")
        self.btn_lock_station.setIcon(IconProvider.get_icon("shield", "#94A3B8", 12))
        self.btn_lock_station.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38BDF8;
                border-color: #38BDF8;
            }
        """)
        self.btn_lock_station.setToolTip("Lock Station / Switch Operator")
        self.btn_lock_station.clicked.connect(self._on_lock_or_switch_user)
        user_top.addWidget(self.btn_lock_station)

        user_card_layout.addLayout(user_top)

        self.lbl_user_name = QLabel("Station Operator")
        self.lbl_user_name.setStyleSheet("color: #F8FAFC; font-size: 11px; font-weight: 700;")
        user_card_layout.addWidget(self.lbl_user_name)

        self.side_layout.addWidget(self.user_card)

        # Compact Rail Bottom Dock (Mini Avatar + Modern Expand Button)
        self.bottom_rail_widget = QWidget()
        b_rail_layout = QVBoxLayout(self.bottom_rail_widget)
        b_rail_layout.setContentsMargins(0, 0, 0, 12)
        b_rail_layout.setSpacing(8)

        self.mini_user_btn = QPushButton()
        self.mini_user_btn.setFixedSize(36, 36)
        self.mini_user_btn.setCursor(Qt.PointingHandCursor)
        self.mini_user_btn.setIcon(IconProvider.get_icon("user", "#38BDF8", 16))
        self.mini_user_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38BDF8;
            }
        """)
        self.mini_user_btn.setToolTip("Sesi Pengguna Aktif (Klik untuk kelola akun)")
        self.mini_user_btn.clicked.connect(self._on_manage_users)
        b_rail_layout.addWidget(self.mini_user_btn, alignment=Qt.AlignCenter)



        self.side_layout.addWidget(self.bottom_rail_widget)
        self.bottom_rail_widget.setVisible(False)


        self.splitter.addWidget(self.sidebar)

        # Right Content Container
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Expand Button Bar (Muncul hanya saat sidebar ditutup sepenuhnya ke 0px)
        self.expand_bar = QWidget()
        expand_layout = QHBoxLayout(self.expand_bar)
        expand_layout.setContentsMargins(16, 10, 16, 0)
        self.btn_expand = QPushButton("☰ Buka Menu")
        self.btn_expand.setObjectName("btnExpandSidebar")
        self.btn_expand.setToolTip("Buka kembali sidebar navigasi")
        self.btn_expand.clicked.connect(self.expand_sidebar)
        expand_layout.addWidget(self.btn_expand)
        expand_layout.addStretch()
        self.expand_bar.setVisible(False)
        content_layout.addWidget(self.expand_bar)

        # Stacked Views Container
        self.stack = QStackedWidget()
        self.dashboard_view = DashboardView()
        self.mqtt_monitor_view = MqttMonitorView()
        self.history_view = HistoryView()
        self.activity_log_view = ActivityLogView()
        self.settings_view = SettingsView()
        self.about_view = AboutView()

        # Connect inter-view signals
        self.dashboard_view.sig_request_monitor.connect(lambda: self.switch_view(1))
        self.dashboard_view.sig_request_history.connect(lambda: self.switch_view(2))
        self.dashboard_view.sig_request_settings.connect(lambda: self.switch_view(4))

        self.stack.addWidget(self.dashboard_view)      # Index 0
        self.stack.addWidget(self.mqtt_monitor_view)   # Index 1
        self.stack.addWidget(self.history_view)        # Index 2
        self.stack.addWidget(self.activity_log_view)   # Index 3
        self.stack.addWidget(self.settings_view)       # Index 4
        self.stack.addWidget(self.about_view)          # Index 5

        content_layout.addWidget(self.stack, stretch=1)
        self.splitter.addWidget(content_container)

        # Set Splitter Properties (Collapsible index 0, Uncollapsible index 1)
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)
        self.splitter.setSizes([self.last_sidebar_width, 950])
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        root_layout.addWidget(self.splitter, stretch=1)

        # Floating Sidebar Edge Toggle Handle Button (Triangle in Middle of Sidebar Edge)
        self.btn_edge_toggle = QPushButton("◀", self)
        self.btn_edge_toggle.setObjectName("btnSidebarEdgeToggle")
        self.btn_edge_toggle.setFixedSize(16, 40)
        self.btn_edge_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_edge_toggle.setToolTip("Ciutkan Sidebar ke Mode Ikon (Rail)")
        self.btn_edge_toggle.clicked.connect(self.toggle_sidebar_rail)

        # Corporate Footer - Internal Enterprise Designation
        footer = QFrame()
        footer.setObjectName("footerFrame")
        footer.setFixedHeight(34)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 0, 16, 0)

        lbl_footer_info = QLabel(f"{APP_NAME} v{APP_VERSION}")
        lbl_footer_info.setObjectName("footerLabel")

        lbl_footer_corp = QLabel("Internal Used by BMES, Property & Development Dept, Enterprise IoT Systems")
        lbl_footer_corp.setObjectName("footerLink")
        lbl_footer_corp.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")

        footer_layout.addWidget(lbl_footer_info)
        footer_layout.addStretch()
        footer_layout.addWidget(lbl_footer_corp)

        root_layout.addWidget(footer)

        # Activate default view
        self.switch_view(0)

    def switch_view(self, index: int):
        # RBAC Security Guard: Operators are restricted to Dashboard (0), Device Monitor (1 - Read Only), Production History (2), and About (5)
        user = auth_service.current_user
        if user and not user.is_admin and index not in (0, 1, 2, 5):
            index = 0

        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Auto refresh when switching views
        if index == 1:
            self.mqtt_monitor_view.refresh_devices()
        elif index == 2:
            self.history_view.load_records()
        elif index == 3:
            self.activity_log_view.load_activities()
        elif index == 4:
            self.settings_view.run_dependency_check()

    def _apply_rail_ui(self, rail_mode: bool):
        """Switches sidebar visual elements between Expanded and Compact Icon Rail mode."""
        self.is_rail_mode = rail_mode
        self.header_expanded.setVisible(not rail_mode)
        self.header_rail.setVisible(rail_mode)

        for btn, item in zip(self.nav_buttons, self.NAV_ITEMS):
            if rail_mode:
                btn.setText("")
                btn.setProperty("compact", "true")
            else:
                btn.setText(f"  {item['title']}")
                btn.setProperty("compact", "false")
            btn.setToolTip(item["tooltip"])
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if hasattr(self, "user_card"):
            self.user_card.setVisible(not rail_mode)
        if hasattr(self, "bottom_rail_widget"):
            self.bottom_rail_widget.setVisible(rail_mode)
        if hasattr(self, "btn_edge_toggle"):
            self.btn_edge_toggle.setText("▶" if rail_mode else "◀")
            self.btn_edge_toggle.setToolTip("Buka Sidebar Penuh" if rail_mode else "Ciutkan Sidebar ke Mode Ikon (Rail)")


    def _update_user_ui(self, user=None):
        """Refreshes the sidebar user profile badge and enforces strict RBAC permissions."""
        user = user or auth_service.current_user
        if not user:
            self.lbl_user_role.setText("UNVERIFIED")
            self.lbl_user_name.setText("Guest")
            return

        is_dev = False
        is_admin = user.is_admin

        if hasattr(self, "mini_user_btn"):
            role_label = "Developer" if is_dev else ("Administrator" if is_admin else "Operator")
            self.mini_user_btn.setToolTip(f"User: {user.username} ({role_label})\nKlik untuk kelola akun")

        if is_dev:
            self.lbl_user_role.setText("ADMIN")
            self.lbl_user_role.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D97706, stop:1 #B45309);
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 800;
                padding: 2px 6px;
                border-radius: 4px;
            """)
        elif is_admin:
            self.lbl_user_role.setText("ADMIN")
            self.lbl_user_role.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1);
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 800;
                padding: 2px 6px;
                border-radius: 4px;
            """)
        else:
            self.lbl_user_role.setText("OPERATOR")
            self.lbl_user_role.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 800;
                padding: 2px 6px;
                border-radius: 4px;
            """)

        self.lbl_user_name.setText(user.display_name)

        # RBAC: Only Admin can manage operator accounts
        if hasattr(self, "btn_manage_users"):
            self.btn_manage_users.setVisible(is_admin)

        # RBAC: Restrict Operators to Dashboard (0), Device Monitor (1), Production History (2), and About (5)
        # Hide sensitive administrative views: Activity Logs (3), Settings (4)
        if hasattr(self, "nav_buttons"):
            for idx, btn in enumerate(self.nav_buttons):
                if idx in (0, 1, 2, 5):
                    btn.setVisible(True)  # Accessible to Operator
                else:
                    btn.setVisible(is_admin)

        # RBAC: Dashboard quick link buttons
        if hasattr(self, "dashboard_view"):
            if hasattr(self.dashboard_view, "btn_open_hist"):
                self.dashboard_view.btn_open_hist.setVisible(True)
            if hasattr(self.dashboard_view, "btn_open_sett"):
                self.dashboard_view.btn_open_sett.setVisible(is_admin)

        # RBAC: Device Monitor Read-Only Mode enforcement
        if hasattr(self, "mqtt_monitor_view"):
            self.mqtt_monitor_view.set_read_only_mode(not is_admin)

        # If currently on a forbidden view when switching user, force redirect to Dashboard
        if not is_admin and self.stack.currentIndex() not in (0, 1, 2, 5):
            self.switch_view(0)

    def _on_manage_users(self):
        """Opens operator management modal dialog (view, add, delete operators)."""
        dlg = UserManagementDialog(self)
        dlg.exec()

    def _on_add_user(self):
        """Opens registration dialog to add a new Operator account."""
        dlg = AddUserDialog(self)
        dlg.exec()

    def _on_change_password(self):
        """Opens self-service password update dialog for currently logged-in account."""
        dlg = ChangePasswordDialog(self)
        dlg.exec()

    def _on_lock_or_switch_user(self):
        """Displays login dialog to switch user or unlock station."""
        login = LoginDialog(self, is_switch_user=True)
        if login.exec() == LoginDialog.Accepted:
            self._update_user_ui()

    def toggle_sidebar_rail(self):
        """Toggles between Expanded mode (~230px) and Compact Icon Rail mode (64px)."""
        sizes = self.splitter.sizes()
        total_width = sum(sizes)
        if self.is_rail_mode or not self.sidebar.isVisible() or sizes[0] < 120:
            target_width = max(self.last_sidebar_width, 220)
            self.sidebar.setVisible(True)
            self.expand_bar.setVisible(False)
            self._apply_rail_ui(False)
            self.splitter.setSizes([target_width, total_width - target_width])
        else:
            if sizes[0] > 120:
                self.last_sidebar_width = sizes[0]
            self.sidebar.setVisible(True)
            self.expand_bar.setVisible(False)
            self._apply_rail_ui(True)
            self.splitter.setSizes([64, total_width - 64])
        self._reposition_toggle_button()

    def collapse_sidebar(self):
        """Collapses sidebar completely to hidden state."""
        sizes = self.splitter.sizes()
        if sizes[0] > 120:
            self.last_sidebar_width = sizes[0]
        self.sidebar.setVisible(False)
        self.expand_bar.setVisible(True)
        self._reposition_toggle_button()

    def expand_sidebar(self):
        """Expands sidebar from fully hidden state and restores expanded width."""
        self.sidebar.setVisible(True)
        width = max(self.last_sidebar_width, 220)
        total_width = sum(self.splitter.sizes())
        self._apply_rail_ui(False)
        self.splitter.setSizes([width, total_width - width])
        self.expand_bar.setVisible(False)
        self._reposition_toggle_button()

    def _on_splitter_moved(self, pos: int, index: int):
        """Handles manual splitter drag events."""
        sizes = self.splitter.sizes()
        sb_w = sizes[0]
        if sb_w <= 15:
            self.sidebar.setVisible(False)
            self.expand_bar.setVisible(True)
        else:
            self.sidebar.setVisible(True)
            self.expand_bar.setVisible(False)
            if sb_w < 130:
                if not self.is_rail_mode:
                    self._apply_rail_ui(True)
            else:
                if self.is_rail_mode:
                    self._apply_rail_ui(False)
                self.last_sidebar_width = sb_w
        self._reposition_toggle_button()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._reposition_toggle_button)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_toggle_button()

    def _reposition_toggle_button(self):
        """Positions the floating triangle handle button precisely in the vertical center of the sidebar border."""
        if not hasattr(self, "btn_edge_toggle") or not hasattr(self, "splitter"):
            return
        try:
            h = self.splitter.handle(1)
            if h and h.isVisible():
                pos = h.mapTo(self, QPoint(0, 0))
                x = pos.x() + (h.width() - self.btn_edge_toggle.width()) // 2
                y = pos.y() + (h.height() - self.btn_edge_toggle.height()) // 2
            else:
                w0 = self.sidebar.width() if self.sidebar.isVisible() else 0
                x = max(0, w0 - self.btn_edge_toggle.width() // 2)
                y = (self.height() - self.btn_edge_toggle.height()) // 2

            self.btn_edge_toggle.move(x, y)
            self.btn_edge_toggle.raise_()

            if self.is_rail_mode or self.sidebar.isHidden():
                self.btn_edge_toggle.setText("▶")
                self.btn_edge_toggle.setToolTip("Buka Sidebar Penuh")
            else:
                self.btn_edge_toggle.setText("◀")
                self.btn_edge_toggle.setToolTip("Ciutkan Sidebar ke Mode Ikon (Rail)")
        except Exception:
            pass

    def closeEvent(self, event):
        """Ensures background network workers and MQTT clients are cleanly stopped."""
        try:
            from src.services.mqtt_service import mqtt_service
            mqtt_service.stop()
        except Exception:
            pass

        try:
            pass
        except Exception:
            pass

        super().closeEvent(event)
