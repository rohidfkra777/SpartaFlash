"""
Topology Configuration Dialog for AlfaEnergy devices.
Provides visual configuration for kodetoko/namapanel/fasa format.
"""

from typing import Optional, List, Set
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QRadioButton, QButtonGroup,
    QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from src.database.models import RegisteredDevice
from src.config.constants import PRODUCT_PLUG, PRODUCT_CT
from src.utils.topology_parser import parse_device_topology, format_device_topology, DeviceTopology


class TopologyConfigDialog(QDialog):
    """
    Dialog for configuring device topology:
    kodetoko / namapanel / fasa
    """

    def __init__(self, parent=None, device: Optional[RegisteredDevice] = None, all_devices: Optional[List[RegisteredDevice]] = None):
        super().__init__(parent)
        self.device = device
        self.all_devices = all_devices or []
        self._topology_result: Optional[str] = None

        self.setWindowTitle("Konfigurasi Topologi & Lokasi Perangkat")
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #CBD5E1;
                font-size: 12px;
            }
            QLineEdit, QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #38BDF8;
                background-color: #0F172A;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                color: #F8FAFC;
                selection-background-color: #0284C7;
                border: 1px solid #334155;
            }
        """)

        self._init_ui()
        self._populate_initial_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Info Card
        header_card = QFrame()
        header_card.setStyleSheet("""
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px;
        """)
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(8, 8, 8, 8)
        h_layout.setSpacing(4)

        lbl_title = QLabel("⚙️  PENGELOMPOKAN PANEL & FASA")
        lbl_title.setStyleSheet("color: #38BDF8; font-weight: 800; font-size: 13px;")
        h_layout.addWidget(lbl_title)

        dev_name = self.device.device_name if self.device else "Unknown"
        dev_mac = self.device.mac_address if self.device else "00:00:00:00:00:00"
        dev_cat = self.device.product_category if self.device else PRODUCT_CT
        lbl_meta = QLabel(f"Device: <b>{dev_name}</b> ({dev_mac}) | Tipe: <b>{dev_cat}</b>")
        lbl_meta.setStyleSheet("color: #94A3B8; font-size: 11px;")
        h_layout.addWidget(lbl_meta)
        layout.addWidget(header_card)

        # 1. Kode Toko
        lbl_store = QLabel("1. Kode Toko:")
        lbl_store.setStyleSheet("font-weight: 700; color: #E2E8F0;")
        layout.addWidget(lbl_store)

        self.txt_store = QLineEdit()
        self.txt_store.setPlaceholderText("Contoh: T105, T042, K012")
        self.txt_store.textChanged.connect(self._on_values_changed)
        layout.addWidget(self.txt_store)

        # 2. Nama Panel / Nama Beban
        lbl_panel = QLabel("2. Nama Panel / Beban:")
        lbl_panel.setStyleSheet("font-weight: 700; color: #E2E8F0;")
        layout.addWidget(lbl_panel)

        self.cmb_panel = QComboBox()
        self.cmb_panel.setEditable(True)
        self.cmb_panel.setInsertPolicy(QComboBox.NoInsert)
        self.cmb_panel.lineEdit().setPlaceholderText("Pilih atau ketik: MDP, CHILLER, AC, OVEN...")
        self.cmb_panel.currentTextChanged.connect(self._on_values_changed)
        layout.addWidget(self.cmb_panel)

        # 3. Fasa / Mode Beban
        lbl_phase = QLabel("3. Fasa / Mode Beban:")
        lbl_phase.setStyleSheet("font-weight: 700; color: #E2E8F0;")
        layout.addWidget(lbl_phase)

        self.cmb_phase = QComboBox()
        self.cmb_phase.addItem("🔴 Fasa R (L1 - 3 Fasa)", "R")
        self.cmb_phase.addItem("🟡 Fasa S (L2 - 3 Fasa)", "S")
        self.cmb_phase.addItem("🔵 Fasa T (L3 - 3 Fasa)", "T")
        self.cmb_phase.addItem("⚪ 1-Fasa (Mandiri / Arus Besar)", "1F")
        self.cmb_phase.addItem("— Tanpa Fasa (Beban Umum / Plug)", "")
        self.cmb_phase.currentIndexChanged.connect(self._on_values_changed)
        layout.addWidget(self.cmb_phase)

        # 4. Preview Box
        preview_box = QFrame()
        preview_box.setStyleSheet("""
            background-color: #0B132B;
            border: 1px dashed #38BDF8;
            border-radius: 8px;
            padding: 10px;
        """)
        p_layout = QVBoxLayout(preview_box)
        p_layout.setContentsMargins(10, 8, 10, 8)
        p_layout.setSpacing(4)

        lbl_pv_title = QLabel("Hasil Format Standar (kodetoko/namapanel/fasa):")
        lbl_pv_title.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 700;")
        p_layout.addWidget(lbl_pv_title)

        self.lbl_preview_code = QLabel("Belum diisi")
        self.lbl_preview_code.setStyleSheet("color: #38BDF8; font-family: 'Consolas', monospace; font-size: 15px; font-weight: 700;")
        p_layout.addWidget(self.lbl_preview_code)

        self.lbl_validation = QLabel("")
        self.lbl_validation.setStyleSheet("color: #F59E0B; font-size: 11px;")
        self.lbl_validation.setWordWrap(True)
        p_layout.addWidget(self.lbl_validation)

        lbl_hw_sync = QLabel("💾 Otomatis tersinkron ke NVS ESP: DeviceName (Header Web) & FriendlyName1 (Tombol Relay)")
        lbl_hw_sync.setStyleSheet("color: #10B981; font-size: 10px; font-weight: 600;")
        p_layout.addWidget(lbl_hw_sync)

        layout.addWidget(preview_box)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_cancel = QPushButton("Batal")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #FFFFFF;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Simpan & Sinkronkan")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0284C7);
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #0369A1;
            }
        """)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)

    def _populate_initial_data(self):
        # Collect existing store codes and panel names for auto-suggestions
        existing_panels: Set[str] = set()
        default_store = ""

        for dev in self.all_devices:
            topo = parse_device_topology(dev.notes)
            if topo.store_code and not default_store:
                default_store = topo.store_code
            if topo.panel_name:
                existing_panels.add(topo.panel_name)

        # Standard recommendations
        common_panels = ["MDP", "CHILLER", "AC", "FREEZER", "OVEN", "SHOWCASE", "KASIR"]
        for cp in common_panels:
            existing_panels.add(cp)

        for p in sorted(existing_panels):
            self.cmb_panel.addItem(p)

        # Parse current device notes
        curr_notes = self.device.notes if self.device else ""
        curr_topo = parse_device_topology(curr_notes)

        if curr_topo.store_code:
            self.txt_store.setText(curr_topo.store_code)
        elif default_store:
            self.txt_store.setText(default_store)

        if curr_topo.panel_name:
            self.cmb_panel.setEditText(curr_topo.panel_name)
        else:
            self.cmb_panel.setEditText("MDP" if (self.device and self.device.product_category == PRODUCT_CT) else "SHOWCASE")

        # Set phase
        if curr_topo.phase in ("R", "S", "T", "1F"):
            idx = self.cmb_phase.findData(curr_topo.phase)
            if idx >= 0:
                self.cmb_phase.setCurrentIndex(idx)
        else:
            # Smart default by category
            if self.device and self.device.product_category == PRODUCT_PLUG:
                idx = self.cmb_phase.findData("")
                if idx >= 0:
                    self.cmb_phase.setCurrentIndex(idx)
            else:
                self.cmb_phase.setCurrentIndex(0)  # Phase R

        self._on_values_changed()

    def _on_values_changed(self):
        store = self.txt_store.text().strip().upper()
        panel = self.cmb_panel.currentText().strip().upper()
        phase = self.cmb_phase.currentData() or ""

        formatted = format_device_topology(store, panel, phase)
        self.lbl_preview_code.setText(formatted if formatted else "(kosong)")

        # Validate duplicate phase in same store & panel
        self.lbl_validation.setText("")
        if store and panel and phase in ("R", "S", "T"):
            for dev in self.all_devices:
                if self.device and dev.mac_address == self.device.mac_address:
                    continue
                other_topo = parse_device_topology(dev.notes)
                if (
                    other_topo.store_code == store
                    and other_topo.panel_name == panel
                    and other_topo.phase == phase
                ):
                    short_mac = dev.mac_address.replace(":", "")[-6:]
                    self.lbl_validation.setText(
                        f"⚠️ Fasa {phase} di {store}/{panel} saat ini sudah dipakai oleh {dev.device_name} ({short_mac})."
                    )
                    break

    def _on_save_clicked(self):
        store = self.txt_store.text().strip().upper()
        panel = self.cmb_panel.currentText().strip().upper()
        phase = self.cmb_phase.currentData() or ""

        self._topology_result = format_device_topology(store, panel, phase)
        self.accept()

    def get_topology_result(self) -> Optional[str]:
        return self._topology_result
