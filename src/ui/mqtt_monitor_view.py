"""
SpartaFlash - Fleet Device Monitor & Live MQTT Cockpit.
Developer: Rohidfkra777

Provides real-time fleet overview, telemetry dashboards (Voltage, Current, Power, Energy),
interactive relay toggling, and an integrated MQTTX-style live traffic console.
"""

import json
from typing import Optional, List, Dict
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSplitter,
    QTextEdit, QMessageBox, QMenu, QDialog, QFormLayout,
    QCheckBox, QInputDialog, QSystemTrayIcon
)
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QColor, QFont, QDesktopServices, QIcon

from src.config.constants import (


    PRODUCT_PLUG,
    PRODUCT_CT,
    APP_ICON_PATH,
)
from src.database.db_manager import db_manager
from src.database.models import RegisteredDevice
from src.services.mqtt_service import mqtt_service
from src.ui.components.icon_provider import IconProvider
from src.utils.topology_parser import parse_device_topology, get_topology_sort_key
from src.ui.components.topology_dialog import TopologyConfigDialog
from src.ui.components.notification_history_dialog import NotificationHistoryDialog
from src.ui.components.wifi_reset_dialog import WifiResetDialog
from src.services.activity_log_service import activity_logger, ActivityCategory, ActivityStatus





class CommandConfirmationDialog(QDialog):
    """
    Industrial safety modal that prompts operators before executing MQTT control commands.
    Provides clear visual warnings for high-risk actions (Power cut, Restart, Energy reset, Buffer clear).
    """

    def __init__(
        self,
        device_name: str,
        topic: str,
        payload: str,
        is_power_cut: bool = False,
        is_power_toggle: bool = False,
        is_restart: bool = False,
        is_reset: bool = False,
        is_clear_buffer: bool = False,
        is_read_only: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Konfirmasi Eksekusi Perintah MQTT")
        self.resize(460, 310)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; border: 1px solid #334155; }
            QLabel { color: #F8FAFC; }
            QCheckBox { color: #94A3B8; font-size: 11px; }
            QPushButton { border-radius: 6px; padding: 7px 16px; font-weight: 700; font-size: 12px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Danger Banner
        banner = QFrame()
        b_color = "#EF4444" if (is_power_cut or is_restart or is_reset or is_clear_buffer) else "#F59E0B" if is_power_toggle else "#38BDF8"
        bg_color = "#450A0A" if (is_power_cut or is_restart or is_reset or is_clear_buffer) else "#451A03" if is_power_toggle else "#0C4A6E"
        banner.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {b_color};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(6, 6, 6, 6)
        b_layout.setSpacing(4)

        if is_power_cut:
            title_text = "⚠️ PERINGATAN KESELAMATAN: PEMUTUSAN DAYA"
            desc_text = "Perintah ini akan MEMATIKAN aliran daya listrik pada perangkat. Pastikan beban listrik aman untuk dimatikan."
        elif is_power_toggle:
            title_text = "⚠️ PERINGATAN: SIKLUS RELAY LISTRIK"
            desc_text = "Perintah ini akan mengubah status saklar relay (ON <-> OFF) secara seketika."
        elif is_restart:
            title_text = "⚠️ PERINGATAN: RESTART SISTEM PERANGKAT"
            desc_text = "Perangkat akan reboot secara remote dan sementara waktu tidak dapat merespon telemetri."
        elif is_clear_buffer:
            title_text = "⚠️ PERINGATAN: PENGHAPUSAN BUFFER OFFLINE"
            desc_text = "Seluruh rekaman telemetri offline di LittleFS flash mikrokontroler akan dihapus permanen."
        elif is_reset:
            title_text = "⚠️ PERINGATAN: RESET DATA ENERGI"
            desc_text = "Akumulasi hitungan kWh pada meteran energi perangkat akan dihapus dan kembali ke nol."
        elif is_read_only:
            title_text = "ℹ️ QUERY TELEMETRI / STATUS BACA"
            desc_text = "Perintah ini bersifat aman (hanya meminta pembacaan status tanpa mempengaruhi beban fisik)."
        else:
            title_text = "⚡ EKSEKUSI PERINTAH KONTROL"
            desc_text = "Pastikan parameter topic dan payload sudah sesuai sebelum dikirimkan ke broker."

        lbl_b_title = QLabel(title_text)
        lbl_b_title.setStyleSheet(f"color: {b_color}; font-weight: 800; font-size: 12px;")
        lbl_b_desc = QLabel(desc_text)
        lbl_b_desc.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        lbl_b_desc.setWordWrap(True)
        b_layout.addWidget(lbl_b_title)
        b_layout.addWidget(lbl_b_desc)
        layout.addWidget(banner)

        # Command Details Box
        detail_frame = QFrame()
        detail_frame.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        detail_layout = QFormLayout(detail_frame)
        detail_layout.setContentsMargins(6, 6, 6, 6)
        detail_layout.setSpacing(6)

        lbl_d_name = QLabel(device_name)
        lbl_d_name.setStyleSheet("font-weight: 700; color: #F8FAFC;")
        lbl_d_topic = QLabel(topic)
        lbl_d_topic.setStyleSheet("font-family: 'Consolas', monospace; color: #38BDF8; font-size: 11px;")
        lbl_d_payload = QLabel(payload)
        lbl_d_payload.setStyleSheet("font-family: 'Consolas', monospace; color: #F59E0B; font-weight: 700;")

        detail_layout.addRow("Perangkat:", lbl_d_name)
        detail_layout.addRow("Topic MQTT:", lbl_d_topic)
        detail_layout.addRow("Payload:", lbl_d_payload)
        layout.addWidget(detail_frame)

        # Checkbox for skipping read-only query confirmation
        self.chk_skip_readonly = QCheckBox("Lewati konfirmasi untuk perintah Query Status (Read-Only)")
        if is_read_only:
            layout.addWidget(self.chk_skip_readonly)
        else:
            self.chk_skip_readonly.hide()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Batal")
        btn_cancel.setProperty("class", "btn-secondary")
        btn_cancel.clicked.connect(self.reject)

        btn_exec = QPushButton("⚡ Ya, Eksekusi Perintah")
        if is_power_cut or is_restart or is_reset:
            btn_exec.setProperty("class", "btn-danger")
        else:
            btn_exec.setProperty("class", "btn-primary")
        btn_exec.clicked.connect(self.accept)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_exec)
        layout.addLayout(btn_box)


class MqttMonitorView(QWidget):
    """
    Real-time Fleet Device Monitor & Live Control Cockpit.
    Seamlessly integrates automatic post-flashing telemetry observation with interactive control.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.devices: List[RegisteredDevice] = []
        self.selected_device: Optional[RegisteredDevice] = None

        self._is_read_only: bool = False
        self._max_console_lines = 400
        self._skip_status_confirm = False
        self._prev_device_statuses: Dict[str, str] = {}
        self._unread_notification_count: int = 0

        # Native Windows Taskbar Notification (strictly no floating in-app toasts)
        self.tray_icon: Optional[QSystemTrayIcon] = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            try:
                self.tray_icon = QSystemTrayIcon(self)
                if APP_ICON_PATH.exists():
                    self.tray_icon.setIcon(QIcon(str(APP_ICON_PATH)))
                elif hasattr(IconProvider, "get_icon"):
                    self.tray_icon.setIcon(IconProvider.get_icon("logo"))
                self.tray_icon.setVisible(True)
            except Exception:
                self.tray_icon = None

        self._init_ui()
        self._setup_signals()

        # Initial data load
        self.refresh_devices()

        # Connect MQTT service in background if not already connected
        if not mqtt_service.is_connected:
            mqtt_service.start()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        # Header Bar
        header_bar = QHBoxLayout()

        title_box = QVBoxLayout()
        lbl_title = QLabel("DEVICE MONITOR & LIVE COCKPIT")
        lbl_title.setStyleSheet("color: #38BDF8; font-size: 20px; font-weight: 800;")
        self.lbl_sub = QLabel("Real-time telemetry and remote control for flashed devices")
        self.lbl_sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(self.lbl_sub)
        header_bar.addLayout(title_box)

        header_bar.addStretch()

        # MQTT Connection Status Indicator
        self.lbl_broker_status = QLabel("○ CONNECTING...")
        self.lbl_broker_status.setFixedHeight(30)
        self.lbl_broker_status.setAlignment(Qt.AlignCenter)
        self.lbl_broker_status.setStyleSheet("""
            background-color: #1E293B;
            color: #F59E0B;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 0px 10px;
            font-weight: 600;
            font-size: 11.5px;
        """)
        header_bar.addWidget(self.lbl_broker_status)

        self.btn_reconnect = QPushButton(" Reconnect")
        self.btn_reconnect.setFixedHeight(30)
        self.btn_reconnect.setIcon(IconProvider.get_icon("refresh-cw", "#94A3B8", 14))
        self.btn_reconnect.setProperty("class", "btn-secondary")
        self.btn_reconnect.clicked.connect(lambda: mqtt_service.start())
        header_bar.addWidget(self.btn_reconnect)

        # Notification Bell & System Audit Log Button
        self.btn_notifications = QPushButton(" Log")
        self.btn_notifications.setFixedHeight(30)
        self.btn_notifications.setToolTip("Log Riwayat Notifikasi & Insiden Sistem (Buffer / Jaringan)")
        self.btn_notifications.clicked.connect(self._open_notification_history)
        self._update_notification_badge()
        header_bar.addWidget(self.btn_notifications)

        root_layout.addLayout(header_bar)

        # Splitter: Left Roster | Right Cockpit & Console
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(6)

        # Left Container: Fleet Device Table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Filter bar
        filter_frame = QFrame()
        filter_frame.setProperty("class", "card")
        filter_bar = QHBoxLayout(filter_frame)
        filter_bar.setContentsMargins(10, 8, 10, 8)
        filter_bar.setSpacing(8)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search device, MAC, IP, keterangan...")
        self.txt_search.textChanged.connect(self.refresh_devices)
        filter_bar.addWidget(self.txt_search, stretch=2)

        # Store Code Dynamic Group Filter (Populated from saved device topology)
        self.cmb_filter_store = QComboBox()
        self.cmb_filter_store.addItem("🏪 Semua Toko (All)", "ALL")
        self.cmb_filter_store.currentIndexChanged.connect(self.refresh_devices)
        filter_bar.addWidget(self.cmb_filter_store, stretch=1)

        self.cmb_filter_cat = QComboBox()
        self.cmb_filter_cat.addItem("All Types", "ALL")
        self.cmb_filter_cat.addItem("Plug", PRODUCT_PLUG)
        self.cmb_filter_cat.addItem("CT", PRODUCT_CT)
        self.cmb_filter_cat.currentIndexChanged.connect(self.refresh_devices)
        filter_bar.addWidget(self.cmb_filter_cat, stretch=1)

        self.cmb_filter_status = QComboBox()
        self.cmb_filter_status.addItem("All Status", "ALL")
        self.cmb_filter_status.addItem("Online Only", "ONLINE")
        self.cmb_filter_status.addItem("Offline Only", "OFFLINE")
        self.cmb_filter_status.currentIndexChanged.connect(self.refresh_devices)
        filter_bar.addWidget(self.cmb_filter_status, stretch=1)

        left_layout.addWidget(filter_frame)

        # Device Table
        self.table_devices = QTableWidget()
        self.table_devices.setColumnCount(7)
        self.table_devices.setHorizontalHeaderLabels([
            "Status", "Device Name", "Type", "Keterangan / Lokasi", "IP Address", "Power", "Relay"
        ])
        self.table_devices.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_devices.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_devices.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table_devices.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_devices.setSelectionMode(QTableWidget.SingleSelection)
        self.table_devices.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table_devices.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_devices.customContextMenuRequested.connect(self._on_table_context_menu)
        self.table_devices.itemSelectionChanged.connect(self._on_device_selected)
        self.table_devices.itemChanged.connect(self._on_table_item_changed)
        left_layout.addWidget(self.table_devices, stretch=1)

        # Fleet summary label
        self.lbl_fleet_summary = QLabel("Total: 0 devices | Online: 0 | Offline: 0")
        self.lbl_fleet_summary.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; padding: 2px;")
        left_layout.addWidget(self.lbl_fleet_summary)

        self.splitter.addWidget(left_widget)

        # Right Container: Selected Device Cockpit & Live Console
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Cockpit Card
        self.cockpit_frame = QFrame()
        self.cockpit_frame.setProperty("class", "card")
        self.cockpit_layout = QVBoxLayout(self.cockpit_frame)
        self.cockpit_layout.setContentsMargins(14, 14, 14, 14)
        self.cockpit_layout.setSpacing(12)

        # Cockpit Header (Device Name, Badges, Quick Actions)
        cockpit_header = QHBoxLayout()
        dev_title_box = QVBoxLayout()
        dev_title_box.setSpacing(4)

        dev_title_row = QHBoxLayout()
        dev_title_row.setSpacing(10)

        self.lbl_cockpit_name = QLabel("Select a Device")
        self.lbl_cockpit_name.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 800;")
        dev_title_row.addWidget(self.lbl_cockpit_name)

        # Interactive Location / Notes Pill Badge (Option 1)
        self.btn_location_pill = QPushButton()
        self.btn_location_pill.setCursor(Qt.PointingHandCursor)
        self.btn_location_pill.clicked.connect(self._edit_current_device_notes)
        self.btn_location_pill.hide()
        dev_title_row.addWidget(self.btn_location_pill)
        dev_title_row.addStretch()

        dev_title_box.addLayout(dev_title_row)

        self.lbl_cockpit_meta = QLabel("Choose a device from the fleet table to monitor live telemetry.")
        self.lbl_cockpit_meta.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.lbl_cockpit_meta.setWordWrap(True)
        dev_title_box.addWidget(self.lbl_cockpit_meta)
        cockpit_header.addLayout(dev_title_box, stretch=1)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(6)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_web_ui = QPushButton(" Web UI")
        self.btn_web_ui.setIcon(IconProvider.get_icon("play", "#38BDF8", 12))
        self.btn_web_ui.setProperty("class", "btn-secondary")
        self.btn_web_ui.setFixedHeight(30)
        self.btn_web_ui.setEnabled(False)
        self.btn_web_ui.clicked.connect(self._open_device_web_ui)
        btn_box.addWidget(self.btn_web_ui)

        self.btn_cmd_query = QPushButton(" Query")
        self.btn_cmd_query.setIcon(IconProvider.get_icon("refresh-cw", "#94A3B8", 12))
        self.btn_cmd_query.setProperty("class", "btn-secondary")
        self.btn_cmd_query.setFixedHeight(30)
        self.btn_cmd_query.setEnabled(False)
        self.btn_cmd_query.clicked.connect(self._send_query_status)
        btn_box.addWidget(self.btn_cmd_query)

        self.btn_cmd_restart = QPushButton(" Restart")
        self.btn_cmd_restart.setIcon(IconProvider.get_icon("rotate-ccw", "#EF4444", 12))
        self.btn_cmd_restart.setProperty("class", "btn-danger")
        self.btn_cmd_restart.setFixedHeight(30)
        self.btn_cmd_restart.setEnabled(False)
        self.btn_cmd_restart.clicked.connect(self._send_restart)
        btn_box.addWidget(self.btn_cmd_restart)

        cockpit_header.addLayout(btn_box)

        self.cockpit_layout.addLayout(cockpit_header)

        # Power Relay Control Banner
        self.relay_banner = QFrame()
        self.relay_banner.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        relay_layout = QHBoxLayout(self.relay_banner)
        relay_layout.setContentsMargins(8, 6, 8, 6)
        relay_layout.setSpacing(8)

        lbl_relay_title = QLabel("RELAY:")
        lbl_relay_title.setStyleSheet("color: #94A3B8; font-weight: 700; font-size: 11px;")
        relay_layout.addWidget(lbl_relay_title)

        self.btn_toggle_power = QPushButton("POWER: UNKNOWN")
        self.btn_toggle_power.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #FFFFFF;
                border: 1px solid #475569;
                border-radius: 6px;
                font-weight: 800;
                font-size: 12px;
                padding: 6px 14px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_toggle_power.setEnabled(False)
        self.btn_toggle_power.clicked.connect(self._send_toggle_power)
        relay_layout.addWidget(self.btn_toggle_power)

        relay_layout.addStretch()

        self.btn_force_on = QPushButton("FORCE ON")
        self.btn_force_on.setProperty("class", "btn-primary")
        self.btn_force_on.setEnabled(False)
        self.btn_force_on.clicked.connect(lambda: self._send_power_direct("ON"))
        relay_layout.addWidget(self.btn_force_on)

        self.btn_force_off = QPushButton("FORCE OFF")
        self.btn_force_off.setProperty("class", "btn-secondary")
        self.btn_force_off.setEnabled(False)
        self.btn_force_off.clicked.connect(lambda: self._send_power_direct("OFF"))
        relay_layout.addWidget(self.btn_force_off)

        self.cockpit_layout.addWidget(self.relay_banner)

        # 4 Telemetry Metrics Cards Grid
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(8)

        self.card_voltage = self._create_metric_card(
            "VOLTAGE", "Grid RMS Voltage", "0.0 V", "V", "#38BDF8", "zap"
        )
        self.card_current = self._create_metric_card(
            "CURRENT", "Instantaneous Load", "0.00 A", "A", "#F59E0B", "zap"
        )
        self.card_power = self._create_metric_card(
            "POWER", "Active Power Draw", "0.0 W", "W", "#10B981", "zap"
        )
        self.card_energy = self._create_metric_card(
            "ENERGY", "Total Consumption", "0.00 kWh", "kWh", "#A855F7", "zap"
        )

        metrics_layout.addWidget(self.card_voltage)
        metrics_layout.addWidget(self.card_current)
        metrics_layout.addWidget(self.card_power)
        metrics_layout.addWidget(self.card_energy)
        self.cockpit_layout.addLayout(metrics_layout)

        right_layout.addWidget(self.cockpit_frame)

        # Live MQTT Console (MQTTX style)
        console_frame = QFrame()
        console_frame.setProperty("class", "card")
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(12, 10, 12, 10)
        console_layout.setSpacing(8)

        # Console Header
        con_header = QHBoxLayout()
        lbl_con_title = QLabel("LIVE MQTT TRAFFIC CONSOLE")
        lbl_con_title.setStyleSheet("color: #38BDF8; font-weight: 800; font-size: 12px; letter-spacing: 0.5px;")
        con_header.addWidget(lbl_con_title)
        con_header.addStretch()

        self.chk_auto_scroll = QCheckBox("Auto-scroll")
        self.chk_auto_scroll.setChecked(True)
        self.chk_auto_scroll.setCursor(Qt.PointingHandCursor)
        self.chk_auto_scroll.setStyleSheet("""
            QCheckBox {
                color: #38BDF8;
                font-size: 11px;
                font-weight: 600;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #334155;
                background-color: #0F172A;
            }
            QCheckBox::indicator:checked {
                background-color: #0284C7;
                border-color: #38BDF8;
            }
        """)
        self.chk_auto_scroll.toggled.connect(self._on_auto_scroll_toggled)
        con_header.addWidget(self.chk_auto_scroll)

        self.btn_clear_log = QPushButton("Clear")
        self.btn_clear_log.setProperty("class", "btn-secondary")
        self.btn_clear_log.clicked.connect(self._clear_console)
        con_header.addWidget(self.btn_clear_log)

        console_layout.addLayout(con_header)

        # Console Log Text Area
        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        # Rolling buffer: keep only last 500 log entries in memory (FIFO)
        self.txt_console.document().setMaximumBlockCount(500)
        self.txt_console.setStyleSheet("""
            QTextEdit {
                background-color: #090D16;
                color: #38BDF8;
                font-family: 'Consolas', 'JetBrains Mono', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        console_layout.addWidget(self.txt_console, stretch=1)

        # Quick Publish Bar (MQTTX style with Presets Dropdown)
        self.pub_widget = QWidget()
        pub_bar = QHBoxLayout(self.pub_widget)
        pub_bar.setContentsMargins(0, 0, 0, 0)
        pub_bar.setSpacing(6)

        lbl_pub = QLabel("Publish:")
        lbl_pub.setStyleSheet("color: #94A3B8; font-weight: 700; font-size: 11px;")
        pub_bar.addWidget(lbl_pub)

        self.cmb_pub_topic = QComboBox()
        self.cmb_pub_topic.setEditable(True)
        self.cmb_pub_topic.setInsertPolicy(QComboBox.NoInsert)
        if self.cmb_pub_topic.lineEdit():
            self.cmb_pub_topic.lineEdit().setPlaceholderText("Topic (cmnd/...)")
        self.cmb_pub_topic.currentTextChanged.connect(self._on_pub_topic_changed)
        pub_bar.addWidget(self.cmb_pub_topic, stretch=3)

        self.cmb_pub_payload = QComboBox()
        self.cmb_pub_payload.setEditable(True)
        self.cmb_pub_payload.setInsertPolicy(QComboBox.NoInsert)
        if self.cmb_pub_payload.lineEdit():
            self.cmb_pub_payload.lineEdit().setPlaceholderText("Payload")
        pub_bar.addWidget(self.cmb_pub_payload, stretch=2)

        self.btn_pub_send = QPushButton(" Send")
        self.btn_pub_send.setIcon(IconProvider.get_icon("play", "#FFFFFF", 12))
        self.btn_pub_send.setProperty("class", "btn-primary")
        self.btn_pub_send.clicked.connect(self._publish_custom_message)
        pub_bar.addWidget(self.btn_pub_send)

        console_layout.addWidget(self.pub_widget)

        right_layout.addWidget(console_frame, stretch=1)

        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([520, 580])
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 6)

        root_layout.addWidget(self.splitter)

    def _create_metric_card(
        self,
        title: str,
        subtitle: str,
        default_val: str,
        unit_badge: str,
        color_hex: str,
        icon_name: str = "zap",
    ) -> QFrame:
        card = QFrame()
        card_id = f"metricCard_{title.lower()}"
        card.setObjectName(card_id)
        card.setStyleSheet(f"""
            QFrame#{card_id} {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                border: 1px solid #334155;
                border-top: 3px solid {color_hex};
                border-radius: 8px;
            }}
            QFrame#{card_id}:hover {{
                border-color: {color_hex};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #24344D, stop:1 #111C2E);
            }}
            QFrame#{card_id} QLabel {{
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """)

        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(12, 10, 12, 10)
        vbox.setSpacing(6)

        # Header Row: Icon + Title on left, 1-Phase Unit Tag on right
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        pixmap = IconProvider.get_pixmap(icon_name, color_hex, 14)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(pixmap)
        header_row.addWidget(lbl_icon)

        lbl_t = QLabel(title.upper())
        lbl_t.setStyleSheet("color: #CBD5E1; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        header_row.addWidget(lbl_t)
        header_row.addStretch()

        badge_text = unit_badge.strip()
        lbl_badge = QLabel(f"1-PHASE • {badge_text}")
        lbl_badge.setStyleSheet("color: #94A3B8; font-size: 9px; font-weight: 700; background-color: #0B1120; border: 1px solid #1E293B; border-radius: 4px; padding: 2px 6px;")
        header_row.addWidget(lbl_badge)

        vbox.addLayout(header_row)

        # Metric Value (Large, bold, monospace)
        lbl_v = QLabel(default_val)
        lbl_v.setObjectName("metricValue")
        lbl_v.setStyleSheet(f"color: {color_hex}; font-size: 24px; font-weight: 900; font-family: 'Consolas', 'Segoe UI', monospace; padding: 2px 0;")
        vbox.addWidget(lbl_v)

        # Subtitle / descriptor
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 600;")
        vbox.addWidget(lbl_sub)

        return card

    def _setup_signals(self):
        mqtt_service.sig_connection_changed.connect(self._on_mqtt_connection_changed)
        mqtt_service.sig_message_received.connect(self._on_mqtt_message_received)
        mqtt_service.sig_device_updated.connect(self._on_device_updated)
        mqtt_service.sig_device_registered.connect(self._on_device_registered)
        mqtt_service.sig_device_event.connect(self._on_device_event)
        mqtt_service.sig_buffer_progress.connect(self._on_buffer_progress)

    def show_taskbar_notification(self, title: str, message: str, is_warning: bool = False):
        """
        Triggers native Windows Taskbar Balloon Notification via QSystemTrayIcon.
        Strictly without floating in-app toasts.
        """
        if self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            icon_type = QSystemTrayIcon.Warning if is_warning else QSystemTrayIcon.Information
            self.tray_icon.showMessage(title, message, icon_type, 6000)

    def set_read_only_mode(self, is_read_only: bool):
        """Enforces strict read-only observer restrictions for Operator role."""
        self._is_read_only = is_read_only
        self.btn_cmd_restart.setVisible(not is_read_only)
        if hasattr(self, "btn_web_ui"):
            self.btn_web_ui.setVisible(not is_read_only)
        if hasattr(self, "pub_widget"):
            self.pub_widget.setVisible(not is_read_only)
        if hasattr(self, "table_devices"):
            self.table_devices.setEditTriggers(
                QTableWidget.NoEditTriggers if is_read_only
                else (QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
            )
        if hasattr(self, "btn_location_pill"):
            self.btn_location_pill.setEnabled(not is_read_only)
        if hasattr(self, "btn_force_on"):
            self.btn_force_on.setVisible(not is_read_only)
        if hasattr(self, "btn_force_off"):
            self.btn_force_off.setVisible(not is_read_only)
        if hasattr(self, "btn_toggle_power") and is_read_only:
            self.btn_toggle_power.setEnabled(False)

    def _open_notification_history(self):
        """Opens the notification history audit modal and resets the unread badge."""
        self._unread_notification_count = 0
        self._update_notification_badge()
        dlg = NotificationHistoryDialog(self)
        dlg.exec()

    def _update_notification_badge(self):
        """Updates bell icon and counter badge based on unread notification count."""
        if not hasattr(self, "btn_notifications"):
            return
        if self._unread_notification_count > 0:
            count_str = str(self._unread_notification_count) if self._unread_notification_count < 100 else "99+"
            self.btn_notifications.setText(f" {count_str}")
            self.btn_notifications.setIcon(IconProvider.get_icon("bell", "#F59E0B", 15))
            self.btn_notifications.setStyleSheet("""
                QPushButton {
                    background-color: #451A03;
                    color: #FCD34D;
                    border: 1px solid #F59E0B;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-weight: 800;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #78350F;
                    border-color: #FBBF24;
                }
            """)
        else:
            self.btn_notifications.setText(" Log")
            self.btn_notifications.setIcon(IconProvider.get_icon("bell", "#94A3B8", 15))
            self.btn_notifications.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #94A3B8;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #F8FAFC;
                    border-color: #475569;
                }
            """)

    def _notify_device_offline(self, dev: RegisteredDevice):
        """Notifies operator via Windows Taskbar when a device loses connection and records audit event."""
        topo = parse_device_topology(dev.notes)
        loc_desc = f" [{topo.store_code}/{topo.panel_name}]" if topo.is_valid else (f" [{dev.notes}]" if dev.notes else "")
        title = "⚠️ Perangkat Terputus (Offline)"
        msg = f"Perangkat {dev.device_name}{loc_desc} terputus dari jaringan. Data telemetri kini disimpan pada buffer LittleFS internal mikrokontroler."
        self.show_taskbar_notification(title, msg, is_warning=True)

        clean_loc = f"{topo.store_code}/{topo.panel_name}" if topo.is_valid else (dev.notes or "")
        try:
            db_manager.insert_system_event(
                mac_address=dev.mac_address,
                device_name=dev.device_name,
                location_desc=clean_loc,
                event_type="OFFLINE",
                downtime_sec=0,
                records_count=0,
                message=msg
            )
            self._unread_notification_count += 1
            self._update_notification_badge()
        except Exception:
            pass

    def _on_device_event(self, mac: str, event_name: str, payload: dict):
        """Handles firmware buffer events (InternetRestored, SyncComplete, BufferStatus) and logs audit trail."""
        dev = next((d for d in self.devices if d.mac_address.upper() == mac.upper()), None)
        dev_name = dev.device_name if dev else f"Device-{mac[-6:]}"
        loc_desc = ""
        clean_loc = ""
        if dev and dev.notes:
            topo = parse_device_topology(dev.notes)
            loc_desc = f" [{topo.store_code}/{topo.panel_name}]" if topo.is_valid else f" [{dev.notes}]"
            clean_loc = f"{topo.store_code}/{topo.panel_name}" if topo.is_valid else dev.notes

        if event_name == "InternetRestored":
            buffered = payload.get("BufferedRecords", 0)
            downtime = payload.get("DowntimeSec", 0)
            mins = downtime // 60
            secs = downtime % 60
            dt_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            title = "🟢 Internet Pulih (Sinkronisasi Dimulai)"
            msg = f"{dev_name}{loc_desc} kembali online (downtime {dt_str}). Menreplay {buffered} rekaman data offline ke database..."
            self.show_taskbar_notification(title, msg, is_warning=False)

            try:
                db_manager.insert_system_event(
                    mac_address=mac,
                    device_name=dev_name,
                    location_desc=clean_loc,
                    event_type="RESTORED",
                    downtime_sec=downtime,
                    records_count=buffered,
                    message=msg
                )
                self._unread_notification_count += 1
                self._update_notification_badge()
            except Exception:
                pass

        elif event_name == "SyncComplete":
            replayed = payload.get("ReplayedRecords", 0)
            title = "✅ Sinkronisasi Offline Selesai"
            msg = f"{replayed} data telemetri offline dari {dev_name}{loc_desc} berhasil disimpan ke database tanpa kendala."
            self.show_taskbar_notification(title, msg, is_warning=False)

            try:
                db_manager.insert_system_event(
                    mac_address=mac,
                    device_name=dev_name,
                    location_desc=clean_loc,
                    event_type="SYNC_COMPLETE",
                    downtime_sec=0,
                    records_count=replayed,
                    message=msg
                )
                self._unread_notification_count += 1
                self._update_notification_badge()
            except Exception:
                pass

        elif event_name == "BufferStatus":
            total_cap = payload.get("TotalCapacity", 12500)
            used = payload.get("UsedRecords", 0)
            max_days = payload.get("MaxDowntimeDays", 8.6)
            self.lbl_cockpit_meta.setText(f"Buffer LittleFS: {used}/{total_cap} records (Kapasitas: {max_days:.1f} hari)")

    def _on_buffer_progress(self, mac: str, seq: int, total: int):
        """Smoothly updates sync progress badge in device table without rebuilding entire table."""
        clean_mac = mac.upper()
        for row in range(self.table_devices.rowCount()):
            if row < len(self.devices) and self.devices[row].mac_address.upper() == clean_mac:
                item = self.table_devices.item(row, 0)
                if item:
                    item.setText(f"● SYNC ({seq}/{total})")
                    item.setForeground(QColor("#38BDF8"))
                    item.setToolTip(f"Sedang mengunduh {seq} dari {total} data offline buffer...")
                break

    def _on_mqtt_connection_changed(self, is_connected: bool, status_text: str):
        if is_connected:
            clean_status = status_text.split("(")[0].strip()
            self.lbl_broker_status.setText(f"● {clean_status}")
            self.lbl_broker_status.setStyleSheet("""
                background-color: #064E3B;
                color: #34D399;
                border: 1px solid #10B981;
                border-radius: 6px;
                padding: 0px 10px;
                font-weight: 600;
                font-size: 11.5px;
            """)
        else:
            clean_status = status_text.split("(")[0].strip()
            self.lbl_broker_status.setText(f"○ {clean_status}")
            self.lbl_broker_status.setStyleSheet("""
                background-color: #450A0A;
                color: #F87171;
                border: 1px solid #EF4444;
                border-radius: 6px;
                padding: 0px 10px;
                font-weight: 600;
                font-size: 11.5px;
            """)

    def _on_mqtt_message_received(self, topic: str, payload: str, timestamp: str):
        # Strict filter: Do NOT show AlfaEnergy/EM-XXXX/# or MC in Live Monitor
        up_topic = topic.upper()
        if "EM-" in up_topic or "/EM" in up_topic or "MC" in up_topic:
            return

        # Format payload if JSON for clean display
        try:
            parsed = json.loads(payload)
            fmt_payload = json.dumps(parsed)
        except Exception:
            fmt_payload = payload

        # Color syntax: green for tele, sky for stat, orange for cmnd
        color = "#10B981" if topic.startswith("tele") else "#38BDF8" if topic.startswith("stat") else "#F59E0B"
        html = f"<span style='color: #64748B;'>[{timestamp}]</span> <b style='color: {color};'>{topic}</b>: <span style='color: #E2E8F0;'>{fmt_payload}</span>"
        self.txt_console.append(html)
        if hasattr(self, "chk_auto_scroll") and self.chk_auto_scroll.isChecked():
            scrollbar = self.txt_console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _on_auto_scroll_toggled(self, checked: bool):
        if checked:
            scrollbar = self.txt_console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _clear_console(self):
        self.txt_console.clear()

    def _on_device_updated(self, mac_address: str):
        # Refresh current row in table and cockpit if selected
        self.refresh_devices(preserve_selection=True)
        if self.selected_device and self.selected_device.mac_address.upper() == mac_address.upper():
            updated = db_manager.get_registered_device(mac_address)
            if updated:
                self.selected_device = updated
                self._update_cockpit(updated)

    def _on_device_registered(self, mac_address: str):
        self.refresh_devices(preserve_selection=True)

    def _update_store_dropdown(self, all_devices: list):
        """
        Dynamically updates the store filter dropdown based on active devices with saved topology.
        Automatically removes store codes when 0 devices belong to that store code (self-cleaning).
        """
        from collections import Counter
        store_counts = Counter()
        unassigned_count = 0

        for dev in all_devices:
            topo = parse_device_topology(dev.notes)
            if topo.store_code and topo.store_code.strip():
                store_counts[topo.store_code.strip().upper()] += 1
            else:
                unassigned_count += 1

        prev_selected = self.cmb_filter_store.currentData()

        new_items = [("ALL", f"🏪 Semua Toko ({len(all_devices)})")]
        for s_code in sorted(store_counts.keys()):
            new_items.append((s_code, f"🏢 {s_code} ({store_counts[s_code]} Perangkat)"))
        if unassigned_count > 0:
            new_items.append(("UNASSIGNED", f"⚠️ Tanpa Toko ({unassigned_count})"))

        current_items = [(self.cmb_filter_store.itemData(i), self.cmb_filter_store.itemText(i)) for i in range(self.cmb_filter_store.count())]
        if current_items == new_items:
            return

        self.cmb_filter_store.blockSignals(True)
        self.cmb_filter_store.clear()

        for data, label in new_items:
            self.cmb_filter_store.addItem(label, data)

        restored_idx = 0
        for i in range(self.cmb_filter_store.count()):
            if self.cmb_filter_store.itemData(i) == prev_selected:
                restored_idx = i
                break

        self.cmb_filter_store.setCurrentIndex(restored_idx)
        self.cmb_filter_store.blockSignals(False)

    def refresh_devices(self, preserve_selection: bool = False):
        search = self.txt_search.text().strip() or None
        cat = self.cmb_filter_cat.currentData()
        status = self.cmb_filter_status.currentData()

        prev_mac = self.selected_device.mac_address if (preserve_selection and self.selected_device) else None

        # Dynamically sync store dropdown with all active registered devices
        all_unfiltered = db_manager.get_all_registered_devices()
        self._update_store_dropdown(all_unfiltered)

        selected_store = self.cmb_filter_store.currentData() or "ALL"

        self.devices = db_manager.get_all_registered_devices(
            filter_status=status,
            filter_category=cat,
            search=search
        )

        # Apply store filter
        if selected_store != "ALL":
            if selected_store == "UNASSIGNED":
                self.devices = [d for d in self.devices if not parse_device_topology(d.notes).store_code]
            else:
                self.devices = [d for d in self.devices if parse_device_topology(d.notes).store_code.upper() == selected_store]

        # Smart topology sorting: groups same store and panel together in R -> S -> T -> 1F order
        self.devices.sort(key=get_topology_sort_key)

        # Approach A: Guarantee strictly 1 row per physical device suffix
        seen_suffixes = set()
        unique_devices = []
        for d in self.devices:
            clean_mac = d.mac_address.replace(":", "").replace("-", "").upper()
            suffix = clean_mac[-6:] if len(clean_mac) >= 6 else clean_mac
            if suffix not in seen_suffixes:
                seen_suffixes.add(suffix)
                unique_devices.append(d)
        self.devices = unique_devices

        online_count = sum(1 for d in self.devices if d.status == "ONLINE")
        offline_count = len(self.devices) - online_count
        store_prefix = f"Toko [{selected_store}] | " if selected_store != "ALL" else ""
        self.lbl_fleet_summary.setText(f"{store_prefix}Total: {len(self.devices)} devices | Online: {online_count} | Offline: {offline_count}")

        self.table_devices.blockSignals(True)
        self.table_devices.setRowCount(len(self.devices))
        restore_row = -1

        for row, dev in enumerate(self.devices):
            # Check offline transition
            prev_st = self._prev_device_statuses.get(dev.mac_address)
            if prev_st == "ONLINE" and dev.status == "OFFLINE":
                self._notify_device_offline(dev)
            self._prev_device_statuses[dev.mac_address] = dev.status

            # 0: Status Badge
            is_online = (dev.status == "ONLINE")
            sync_info = mqtt_service._buffer_sync_trackers.get(dev.mac_address)
            if sync_info and sync_info.get("total", 0) > 0:
                seq = sync_info.get("seq", 0)
                total = sync_info.get("total", 0)
                status_item = QTableWidgetItem(f"● SYNC ({seq}/{total})")
                status_item.setForeground(QColor("#38BDF8"))
                status_item.setToolTip(f"Sedang mengunduh {seq} dari {total} data offline buffer LittleFS...")
            elif is_online:
                status_item = QTableWidgetItem("● ONLINE")
                status_item.setForeground(QColor("#34D399"))
            else:
                status_item = QTableWidgetItem("○ OFFLINE")
                status_item.setForeground(QColor("#94A3B8"))
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_devices.setItem(row, 0, status_item)

            # 1: Device Name (Option A: Concise 6 digits MAC suffix)
            short_name = dev.device_name.split("-")[-1] if "-" in dev.device_name else dev.device_name
            name_item = QTableWidgetItem(short_name)
            name_item.setFont(QFont("Consolas", 10, QFont.Bold))
            name_item.setTextAlignment(Qt.AlignCenter)
            name_item.setToolTip(f"Perangkat: {dev.device_name}\nHardware MAC: {dev.mac_address}")
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_devices.setItem(row, 1, name_item)

            # 2: Type (Plug / CT)
            is_plug = (dev.product_category == PRODUCT_PLUG)
            type_text = "Plug" if is_plug else "CT"
            type_item = QTableWidgetItem(type_text)
            type_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            type_item.setTextAlignment(Qt.AlignCenter)
            type_item.setForeground(QColor("#38BDF8" if is_plug else "#F59E0B"))
            type_item.setToolTip(f"Kategori: {dev.product_category}")
            type_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_devices.setItem(row, 2, type_item)

            # 3: Keterangan / Lokasi (Smart parsed with phase badge)
            topo = parse_device_topology(dev.notes)
            if dev.notes:
                if topo.is_three_phase:
                    display_text = f"{topo.store_code}/{topo.panel_name}  [{topo.phase}]"
                    notes_item = QTableWidgetItem(display_text)
                    notes_item.setForeground(QColor(topo.phase_color))
                    notes_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    notes_item.setToolTip(f"Panel 3-Fasa: {topo.panel_name} (Fasa {topo.phase})\nToko: {topo.store_code}\nFormat: {dev.notes}\n(Klik ganda untuk mengubah)")
                elif topo.is_valid:
                    display_text = f"{topo.store_code}/{topo.panel_name}" + (f"  [{topo.phase}]" if topo.phase else "")
                    notes_item = QTableWidgetItem(display_text)
                    notes_item.setForeground(QColor("#38BDF8"))
                    notes_item.setToolTip(f"Beban Mandiri: {topo.panel_name} ({topo.phase or '1F'})\nToko: {topo.store_code}\nFormat: {dev.notes}\n(Klik ganda untuk mengubah)")
                else:
                    notes_item = QTableWidgetItem(dev.notes)
                    notes_item.setForeground(QColor("#38BDF8"))
                    notes_item.setToolTip(f"Keterangan: {dev.notes}\n(Klik ganda untuk mengubah)")
            else:
                notes_item = QTableWidgetItem("")
                notes_item.setForeground(QColor("#64748B"))
                notes_item.setToolTip("Klik ganda untuk mengisi format kodetoko/namapanel/fasa")
            notes_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            self.table_devices.setItem(row, 3, notes_item)

            # 4: IP Address
            ip_item = QTableWidgetItem(dev.ip_address or "-")
            ip_item.setTextAlignment(Qt.AlignCenter)
            ip_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_devices.setItem(row, 4, ip_item)

            # 5: Power (W)
            power_val = f"{dev.power:.1f} W" if dev.status == "ONLINE" else "-"
            power_item = QTableWidgetItem(power_val)
            power_item.setTextAlignment(Qt.AlignCenter)
            power_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_devices.setItem(row, 5, power_item)

            # 6: Relay State
            p_state = dev.power_state if dev.power_state else "UNKNOWN"
            relay_item = QTableWidgetItem(p_state)
            if p_state == "ON":
                relay_item.setForeground(QColor("#10B981"))
            elif p_state == "OFF":
                relay_item.setForeground(QColor("#EF4444"))
            relay_item.setTextAlignment(Qt.AlignCenter)
            relay_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_devices.setItem(row, 6, relay_item)

            if prev_mac and dev.mac_address == prev_mac:
                restore_row = row

        self.table_devices.blockSignals(False)

        if restore_row >= 0:
            self.table_devices.selectRow(restore_row)

    def _on_device_selected(self):
        selected_rows = self.table_devices.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_device = None
            self._disable_cockpit()
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.devices):
            self.selected_device = self.devices[row]
            self._update_cockpit(self.selected_device)

    def _update_cockpit(self, dev: RegisteredDevice):
        is_online = (dev.status == "ONLINE")
        is_plug = (dev.product_category == PRODUCT_PLUG)

        self.lbl_cockpit_name.setText(dev.device_name)
        if dev.notes:
            topo = parse_device_topology(dev.notes)
            if topo.is_three_phase:
                self.btn_location_pill.setText(f"🏷️  {topo.store_code}/{topo.panel_name} • Fasa {topo.phase}")
                self.btn_location_pill.setToolTip(f"Panel 3-Fasa: {topo.panel_name} (Fasa {topo.phase}) | Toko: {topo.store_code}\n(Klik untuk mengubah)")
                self.btn_location_pill.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #1E293B;
                        color: {topo.phase_color};
                        border: 1px solid {topo.phase_color};
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 10px;
                    }}
                    QPushButton:hover {{
                        background-color: {topo.phase_color};
                        color: #0F172A;
                    }}
                """)
            elif topo.is_valid:
                p_text = f" ({topo.phase})" if topo.phase else ""
                self.btn_location_pill.setText(f"🏷️  {topo.store_code}/{topo.panel_name}{p_text}")
                self.btn_location_pill.setToolTip(f"Beban Mandiri: {topo.panel_name} | Toko: {topo.store_code}\n(Klik untuk mengubah)")
                self.btn_location_pill.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0C4A6E, stop:1 #075985);
                        color: #38BDF8;
                        border: 1px solid #0284C7;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 10px;
                    }
                    QPushButton:hover {
                        background: #0284C7;
                        color: #FFFFFF;
                        border-color: #38BDF8;
                    }
                """)
            else:
                self.btn_location_pill.setText(f"🏷️  {dev.notes}")
                self.btn_location_pill.setToolTip(f"Keterangan: {dev.notes}\n(Klik untuk mengubah)")
                self.btn_location_pill.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0C4A6E, stop:1 #075985);
                        color: #38BDF8;
                        border: 1px solid #0284C7;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 10px;
                    }
                    QPushButton:hover {
                        background: #0284C7;
                        color: #FFFFFF;
                        border-color: #38BDF8;
                    }
                """)
        else:
            self.btn_location_pill.setText("+ Set Panel / Lokasi")
            self.btn_location_pill.setToolTip("Klik untuk mengatur Toko, Panel, dan Fasa (kodetoko/namapanel/fasa)")
            self.btn_location_pill.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #94A3B8;
                    border: 1px dashed #475569;
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #F8FAFC;
                    border-color: #94A3B8;
                }
            """)
        self.btn_location_pill.show()

        ip_txt = dev.ip_address or "IP Unknown"
        rssi_txt = f"{dev.wifi_rssi} dBm" if dev.wifi_rssi else "RSSI N/A"
        wifi_txt = f"{dev.wifi_ssid} ({rssi_txt})" if (dev.wifi_ssid and dev.wifi_rssi) else (dev.wifi_ssid or "N/A")
        status_color = "#34D399" if is_online else "#F87171"
        status_tag = f"<span style='color: {status_color}; font-weight: 700;'>{'● ONLINE' if is_online else '○ OFFLINE'}</span>"
        self.lbl_cockpit_meta.setText(
            f"MAC: {dev.mac_address} | Type: {dev.product_category} | IP: {ip_txt} | WiFi: {wifi_txt} | Status: {status_tag}"
        )

        # Web UI, Query, and Restart buttons
        self.btn_web_ui.setVisible(not self._is_read_only)
        self.btn_web_ui.setEnabled(bool(dev.ip_address and is_online and not self._is_read_only))
        self.btn_cmd_query.setEnabled(is_online)
        self.btn_cmd_restart.setVisible(not self._is_read_only)
        self.btn_cmd_restart.setEnabled(is_online and not self._is_read_only)

        if self._is_read_only:
            self.btn_location_pill.setEnabled(False)
            self.btn_location_pill.setToolTip(f"Panel & Fasa: {dev.notes or 'Belum diatur'} (Hanya Administrator yang dapat mengubah)")

        # Relay button logic (available for both Plug and CT)
        self.relay_banner.show()
        p_state = dev.power_state.upper()

        if self._is_read_only:
            self.btn_toggle_power.setEnabled(False)
            self.btn_force_on.setVisible(False)
            self.btn_force_off.setVisible(False)
            if p_state == "ON":
                self.btn_toggle_power.setText("● RELAY STATUS: ON (READ-ONLY)")
                self.btn_toggle_power.setStyleSheet("""
                    QPushButton {
                        background-color: #064E3B;
                        color: #6EE7B7;
                        border: 1px solid #10B981;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 13px;
                        padding: 8px 18px;
                    }
                """)
            elif p_state == "OFF":
                self.btn_toggle_power.setText("○ RELAY STATUS: OFF (READ-ONLY)")
                self.btn_toggle_power.setStyleSheet("""
                    QPushButton {
                        background-color: #450A0A;
                        color: #FCA5A5;
                        border: 1px solid #EF4444;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 13px;
                        padding: 8px 18px;
                    }
                """)
            else:
                self.btn_toggle_power.setText("RELAY STATUS: UNKNOWN (READ-ONLY)")
                self.btn_toggle_power.setStyleSheet("""
                    QPushButton {
                        background-color: #1E293B;
                        color: #94A3B8;
                        border: 1px solid #334155;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 13px;
                        padding: 8px 18px;
                    }
                """)
        else:
            self.btn_force_on.setVisible(True)
            self.btn_force_off.setVisible(True)
            self.btn_toggle_power.setEnabled(is_online)
            self.btn_force_on.setEnabled(is_online)
            self.btn_force_off.setEnabled(is_online)

            if p_state == "ON":
                self.btn_toggle_power.setText("⚡ POWER: ON (CLICK TO TOGGLE)")
                self.btn_toggle_power.setStyleSheet("""
                    QPushButton {
                        background-color: #065F46;
                        color: #6EE7B7;
                        border: 1px solid #10B981;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 13px;
                        padding: 8px 18px;
                    }
                    QPushButton:hover { background-color: #047857; }
                """)
            elif p_state == "OFF":
                self.btn_toggle_power.setText("○ POWER: OFF (CLICK TO TOGGLE)")
                self.btn_toggle_power.setStyleSheet("""
                    QPushButton {
                        background-color: #450A0A;
                        color: #FCA5A5;
                        border: 1px solid #EF4444;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 13px;
                        padding: 8px 18px;
                    }
                    QPushButton:hover { background-color: #7F1D1D; }
                """)
            else:
                self.btn_toggle_power.setText("POWER: UNKNOWN")
                self.btn_toggle_power.setStyleSheet("""
                    QPushButton {
                        background-color: #334155;
                        color: #F8FAFC;
                        border: 1px solid #475569;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 13px;
                        padding: 8px 18px;
                    }
                """)

        # Telemetry metrics
        lbl_v = self.card_voltage.findChild(QLabel, "metricValue")
        if lbl_v:
            lbl_v.setText(f"{dev.voltage:.1f} V" if is_online else "---")

        lbl_c = self.card_current.findChild(QLabel, "metricValue")
        if lbl_c:
            lbl_c.setText(f"{dev.current:.2f} A" if is_online else "---")

        lbl_p = self.card_power.findChild(QLabel, "metricValue")
        if lbl_p:
            lbl_p.setText(f"{dev.power:.1f} W" if is_online else "---")

        lbl_e = self.card_energy.findChild(QLabel, "metricValue")
        if lbl_e:
            lbl_e.setText(f"{dev.energy:.2f} kWh" if is_online else "---")

        # Update preset topics in dropdown for current device
        mac_key = mqtt_service.get_device_topic_key(dev.mac_address)
        self.cmb_pub_topic.blockSignals(True)
        self.cmb_pub_topic.clear()
        if is_plug:
            topic_presets = [
                f"AlfaEnergy/Plug/{mac_key}/cmnd/Power",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/Status",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/DeviceName",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/FriendlyName1",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/BufferStatus",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/BufferClear",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/TelePeriod",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/Restart",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/Upgrade",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/EnergyReset",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/WifiReset",
                f"AlfaEnergy/Plug/{mac_key}/cmnd/Reset",
                "AlfaEnergy/Plug/alfaenergy_plug_all/cmnd/Upgrade",
            ]
        else:
            topic_presets = [
                f"AlfaEnergy/CT/{mac_key}/cmnd/Power",
                f"AlfaEnergy/CT/{mac_key}/cmnd/Status",
                f"AlfaEnergy/CT/{mac_key}/cmnd/DeviceName",
                f"AlfaEnergy/CT/{mac_key}/cmnd/FriendlyName1",
                f"AlfaEnergy/CT/{mac_key}/cmnd/BufferStatus",
                f"AlfaEnergy/CT/{mac_key}/cmnd/BufferClear",
                f"AlfaEnergy/CT/{mac_key}/cmnd/TelePeriod",
                f"AlfaEnergy/CT/{mac_key}/cmnd/Restart",
                f"AlfaEnergy/CT/{mac_key}/cmnd/Upgrade",
                f"AlfaEnergy/CT/{mac_key}/cmnd/EnergyReset",
                f"AlfaEnergy/CT/{mac_key}/cmnd/WifiReset",
                f"AlfaEnergy/CT/{mac_key}/cmnd/Reset",
                "AlfaEnergy/CT/alfaenergy_ct_all/cmnd/Upgrade",
            ]
        self.cmb_pub_topic.addItems(topic_presets)
        self.cmb_pub_topic.blockSignals(False)
        self._on_pub_topic_changed(self.cmb_pub_topic.currentText())

    def _disable_cockpit(self):
        self.lbl_cockpit_name.setText("Select a Device")
        self.btn_location_pill.hide()
        self.lbl_cockpit_meta.setText("Choose a device from the fleet table to monitor live telemetry.")
        self.btn_web_ui.setVisible(not getattr(self, "_is_read_only", False))
        self.btn_web_ui.setEnabled(False)
        self.btn_cmd_query.setEnabled(False)
        self.btn_cmd_restart.setVisible(not getattr(self, "_is_read_only", False))
        self.btn_cmd_restart.setEnabled(False)
        self.btn_toggle_power.setEnabled(False)
        self.btn_force_on.setEnabled(False)
        self.btn_force_off.setEnabled(False)

        self.cmb_pub_topic.blockSignals(True)
        self.cmb_pub_topic.clear()
        self.cmb_pub_topic.blockSignals(False)
        self.cmb_pub_payload.blockSignals(True)
        self.cmb_pub_payload.clear()
        self.cmb_pub_payload.blockSignals(False)

        for card in [self.card_voltage, self.card_current, self.card_power, self.card_energy]:
            lbl = card.findChild(QLabel, "metricValue")
            if lbl:
                lbl.setText("---")

    def _on_pub_topic_changed(self, topic: str):
        """Dynamically populates payload options based on selected topic suffix."""
        clean_topic = topic.strip().lower()
        self.cmb_pub_payload.blockSignals(True)
        curr_text = self.cmb_pub_payload.currentText()
        self.cmb_pub_payload.clear()

        if clean_topic.endswith("/power"):
            self.cmb_pub_payload.addItems(["TOGGLE", "ON", "OFF", "STATUS"])
        elif clean_topic.endswith("/status"):
            self.cmb_pub_payload.addItems(["8 (Power & Sensors)", "0 (All Data)", "5 (Network & WiFi)", "1 (System Status)"])
        elif clean_topic.endswith("/bufferstatus"):
            self.cmb_pub_payload.addItems(["1 (Query Used/Total Records)"])
        elif clean_topic.endswith("/bufferclear"):
            self.cmb_pub_payload.addItems(["1 (Format & Erase LittleFS Buffer)"])
        elif clean_topic.endswith("/teleperiod"):
            self.cmb_pub_payload.addItems(["30 (30 Seconds)", "10 (10 Seconds)", "60 (1 Minute)", "300 (5 Minutes)"])
        elif clean_topic.endswith("/restart"):
            self.cmb_pub_payload.addItems(["1 (Reboot System)"])
        elif clean_topic.endswith("/upgrade"):
            self.cmb_pub_payload.addItems(["1 (Trigger OTA Upgrade)", "2 (Force Reinstall)"])
        elif clean_topic.endswith("/energyreset"):
            self.cmb_pub_payload.addItems(["1 (Reset Today)", "3 (Reset Total kWh)", "0 (Reset All kWh)"])
        elif clean_topic.endswith("/wifireset"):
            self.cmb_pub_payload.addItems(["4 (Reset Wi-Fi -> Hotspot AP / SSID Baru)"])
        elif clean_topic.endswith("/reset"):
            self.cmb_pub_payload.addItems(["4 (Reset Wi-Fi -> Hotspot AP / SSID Baru)", "1 (Hard Factory Reset Total)"])
        elif clean_topic.endswith("/devicename") or clean_topic.endswith("/friendlyname1") or clean_topic.endswith("/friendlyname"):
            curr_loc = self.selected_device.notes if self.selected_device and self.selected_device.notes else "T104/P-UTAMA/R"
            self.cmb_pub_payload.addItems([curr_loc, "0 (Reset Default)"])
        else:
            if curr_text:
                self.cmb_pub_payload.addItem(curr_text)

        self.cmb_pub_payload.blockSignals(False)

    def _confirm_and_publish(self, topic: str, payload: str, device_name: Optional[str] = None) -> bool:
        """
        Displays an industrial safety confirmation modal before sending MQTT control messages.
        Differentiates high-risk actions (Power cut, Restart, Energy reset, Buffer clear) from safe read-only queries.
        """
        dev_name = device_name or (self.selected_device.device_name if self.selected_device else "Target Device")

        # Smart Command Translation for Modern Tasmota (v9.5+)
        # Translates legacy EnergyReset selections to native EnergyToday, EnergyTotal, or Backlog
        if topic.strip().lower().endswith("/energyreset"):
            prefix = topic[:topic.rfind("/")]
            if "1" in payload.upper() or "TODAY" in payload.upper():
                topic = f"{prefix}/EnergyToday"
                payload = "0"
            elif "3" in payload.upper() or "TOTAL" in payload.upper():
                topic = f"{prefix}/EnergyTotal"
                payload = "0"
            else:
                topic = f"{prefix}/Backlog"
                payload = "EnergyTotal 0; EnergyToday 0; EnergyYesterday 0"

        clean_topic = topic.lower()
        clean_payload = payload.upper()

        is_wifi_reset = ("/wifireset" in clean_topic) or ("/reset" in clean_topic and ("4" in clean_payload or "WIFI" in clean_payload))
        if is_wifi_reset:
            mac_key = mqtt_service.get_device_topic_key(self.selected_device.mac_address) if self.selected_device else "UNKNOWN"
            cat = "Plug" if (self.selected_device and self.selected_device.product_category == PRODUCT_PLUG) else "CT"
            dlg = WifiResetDialog(device_name=dev_name, mac_key=mac_key, parent=self)
            if dlg.exec() == QDialog.Accepted:
                plan = dlg.get_execution_plan()
                # 1. Reset kWh if requested
                if plan.get("reset_kwh"):
                    mqtt_service.publish_raw(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Backlog", "EnergyTotal 0; EnergyToday 0; EnergyYesterday 0")
                # 2. Clear LittleFS buffer if requested
                if plan.get("clear_buffer"):
                    mqtt_service.publish_raw(f"AlfaEnergy/{cat}/{mac_key}/cmnd/BufferClear", "1")
                # 3. Wi-Fi handover
                if plan.get("method") == "DIRECT":
                    mqtt_service.publish_raw(f"AlfaEnergy/{cat}/{mac_key}/cmnd/SSId1", plan.get("ssid", ""))
                    mqtt_service.publish_raw(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Password1", plan.get("password", ""))
                    mqtt_service.publish_raw(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Restart", "1")
                else:
                    mqtt_service.publish_raw(f"AlfaEnergy/{cat}/{mac_key}/cmnd/WifiConfig", "2")
                    mqtt_service.publish_raw(f"AlfaEnergy/{cat}/{mac_key}/cmnd/SSId1", "")
                    mqtt_service.publish_raw(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Reset", "4")
                activity_logger.log(
                    category=ActivityCategory.SENSITIVE,
                    action="RESET_WIFI",
                    details=f"Device: {dev_name} ({mac_key}), Mode: {plan.get('method')}, Reset kWh: {plan.get('reset_kwh')}, Clear Buffer: {plan.get('clear_buffer')}",
                    status=ActivityStatus.WARNING
                )
                return True
            return False

        is_power_cut = ("/power" in clean_topic and clean_payload in ("OFF", "0"))
        is_power_toggle = ("/power" in clean_topic and clean_payload in ("TOGGLE", "2"))
        is_restart = ("/restart" in clean_topic)
        is_clear_buffer = ("/bufferclear" in clean_topic)
        is_reset = ("/energyreset" in clean_topic or "/energytotal" in clean_topic or "/energytoday" in clean_topic or "/reset" in clean_topic or is_clear_buffer or ("backlog" in clean_topic and "energy" in clean_payload.lower()))
        is_read_only = ("/status" in clean_topic or "/teleperiod" in clean_topic or "/bufferstatus" in clean_topic or clean_payload in ("STATUS", ""))

        # If read-only query and operator selected to skip confirmation
        if is_read_only and self._skip_status_confirm:
            return mqtt_service.publish_raw(topic, payload)

        dlg = CommandConfirmationDialog(
            device_name=dev_name,
            topic=topic,
            payload=payload,
            is_power_cut=is_power_cut,
            is_power_toggle=is_power_toggle,
            is_restart=is_restart,
            is_reset=is_reset,
            is_clear_buffer=is_clear_buffer,
            is_read_only=is_read_only,
            parent=self
        )

        if dlg.exec() == QDialog.Accepted:
            if is_read_only and dlg.chk_skip_readonly.isChecked():
                self._skip_status_confirm = True
            return mqtt_service.publish_raw(topic, payload)
        return False

    def _open_device_web_ui(self):
        if getattr(self, "_is_read_only", False):
            return
        if self.selected_device and self.selected_device.ip_address:
            url = f"http://{self.selected_device.ip_address}"
            QDesktopServices.openUrl(QUrl(url))

    def _send_toggle_power(self):
        if getattr(self, "_is_read_only", False):
            return
        if self.selected_device:
            mac_key = mqtt_service.get_device_topic_key(self.selected_device.mac_address)
            cat = "Plug" if self.selected_device.product_category == PRODUCT_PLUG else "CT"
            self._confirm_and_publish(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Power", "TOGGLE")

    def _send_power_direct(self, state: str):
        if getattr(self, "_is_read_only", False):
            return
        if self.selected_device:
            mac_key = mqtt_service.get_device_topic_key(self.selected_device.mac_address)
            cat = "Plug" if self.selected_device.product_category == PRODUCT_PLUG else "CT"
            self._confirm_and_publish(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Power", state)

    def _send_restart(self):
        if getattr(self, "_is_read_only", False):
            return
        if self.selected_device:
            mac_key = mqtt_service.get_device_topic_key(self.selected_device.mac_address)
            cat = "Plug" if self.selected_device.product_category == PRODUCT_PLUG else "CT"
            self._confirm_and_publish(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Restart", "1")

    def _send_query_status(self):
        if self.selected_device:
            mac_key = mqtt_service.get_device_topic_key(self.selected_device.mac_address)
            cat = "Plug" if self.selected_device.product_category == PRODUCT_PLUG else "CT"
            # Status 0 queries all submodules (Network Status 5 for IP, and Sensors Status 8 for telemetry)
            self._confirm_and_publish(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Status", "0")

    def _publish_custom_message(self):
        if getattr(self, "_is_read_only", False):
            QMessageBox.warning(self, "Akses Ditolak", "Operator hanya memiliki hak akses pemantauan (Read-Only).")
            return
        topic = self.cmb_pub_topic.currentText().strip()
        raw_payload = self.cmb_pub_payload.currentText().strip()
        if not topic:
            QMessageBox.warning(self, "Missing Topic", "Please specify an MQTT topic to publish.")
            return

        # Extract primary command value if description is present (e.g. "8 (Power & Sensors)" -> "8")
        payload = raw_payload.split(" ")[0].strip() if " (" in raw_payload else raw_payload
        self._confirm_and_publish(topic, payload)

    def _on_table_context_menu(self, pos):
        item = self.table_devices.itemAt(pos)
        if not item:
            return

        row = item.row()
        if row < 0 or row >= len(self.devices):
            return

        dev = self.devices[row]
        mac_key = mqtt_service.get_device_topic_key(dev.mac_address)
        cat = "Plug" if dev.product_category == PRODUCT_PLUG else "CT"
        menu = QMenu(self)

        if getattr(self, "_is_read_only", False):
            # Strict Read-Only Mode for Operators: only safe passive inspection (Query Status)
            act_query = menu.addAction("Query Status")
            action = menu.exec(self.table_devices.viewport().mapToGlobal(pos))
            if action == act_query:
                self._confirm_and_publish(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Status", "8", dev.device_name)
            return

        act_edit_notes = menu.addAction("⚙️  Konfigurasi Panel & Fasa...")
        menu.addSeparator()
        act_query = menu.addAction("Query Status")
        act_restart = menu.addAction("Restart Device")
        act_toggle = menu.addAction("Toggle Power")
        if dev.ip_address:
            act_web = menu.addAction(f"Open Web UI ({dev.ip_address})")
        menu.addSeparator()
        act_delete = menu.addAction("Remove from Roster")

        action = menu.exec(self.table_devices.viewport().mapToGlobal(pos))
        if action == act_edit_notes:
            self._prompt_edit_notes(dev)
        elif action == act_query:
            self._confirm_and_publish(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Status", "8", dev.device_name)
        elif action == act_restart:
            self._confirm_and_publish(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Restart", "1", dev.device_name)
        elif action == act_toggle:
            self._confirm_and_publish(f"AlfaEnergy/{cat}/{mac_key}/cmnd/Power", "TOGGLE", dev.device_name)
        elif dev.ip_address and action == act_web:
            QDesktopServices.openUrl(QUrl(f"http://{dev.ip_address}"))
        elif action == act_delete:
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Remove {dev.device_name} from device monitoring roster?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                mqtt_service.unsubscribe_device(dev.mac_address)
                db_manager.delete_registered_device(dev.mac_address)
                self.refresh_devices()

    def _on_table_item_changed(self, item: QTableWidgetItem):
        """Handles in-place cell editing for the 'Keterangan / Lokasi' column."""
        if item.column() != 3:
            return
        row = item.row()
        if 0 <= row < len(self.devices):
            dev = self.devices[row]
            new_notes = item.text().strip() or None
            if dev.notes != new_notes:
                dev.notes = new_notes
                mqtt_service.sync_device_notes(dev.mac_address, new_notes, dev.product_category)
                self.refresh_devices(preserve_selection=True)
                if self.selected_device and self.selected_device.mac_address == dev.mac_address:
                    self.selected_device.notes = new_notes
                    self._update_cockpit(self.selected_device)

    def _edit_current_device_notes(self):
        """Action for the Cockpit 'Lokasi' button."""
        if self.selected_device:
            self._prompt_edit_notes(self.selected_device)

    def _prompt_edit_notes(self, dev: RegisteredDevice):
        """Displays structured modal dialog for editing device topology (kodetoko/namapanel/fasa)."""
        dlg = TopologyConfigDialog(self, device=dev, all_devices=self.devices)
        if dlg.exec() == QDialog.Accepted:
            new_notes = dlg.get_topology_result()
            dev.notes = new_notes
            mqtt_service.sync_device_notes(dev.mac_address, new_notes, dev.product_category)
            self.refresh_devices(preserve_selection=True)
            if self.selected_device and self.selected_device.mac_address == dev.mac_address:
                self.selected_device.notes = new_notes
                self._update_cockpit(self.selected_device)

    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(500, 350)
