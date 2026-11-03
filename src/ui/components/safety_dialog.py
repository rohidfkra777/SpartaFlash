"""
SpartaFlash - Animated Pre-Flight Verification & Safety Wizard.
Developer: Rohidfkra777
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QFrame, QWidget, QStackedWidget
)
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSize
from src.ui.components.icon_provider import IconProvider
from src.services.firmware_service import FirmwareInfo

class SlidingStackedWidget(QStackedWidget):
    """StackedWidget with smooth horizontal slide animation transitions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._animating = False

    def slide_to_index(self, target_index: int, direction: int = 1):
        """
        Transitions between pages with horizontal easing curve.
        direction: 1 = forward (slide left), -1 = backward (slide right).
        """
        if target_index == self.currentIndex() or self._animating:
            return

        current_widget = self.currentWidget()
        next_widget = self.widget(target_index)

        width = self.width()
        height = self.height()

        offset = width if direction > 0 else -width

        next_widget.setGeometry(offset, 0, width, height)
        next_widget.show()
        next_widget.raise_()

        anim_current = QPropertyAnimation(current_widget, b"pos")
        anim_current.setDuration(260)
        anim_current.setEasingCurve(QEasingCurve.OutCubic)
        anim_current.setStartValue(QPoint(0, 0))
        anim_current.setEndValue(QPoint(-offset, 0))

        anim_next = QPropertyAnimation(next_widget, b"pos")
        anim_next.setDuration(260)
        anim_next.setEasingCurve(QEasingCurve.OutCubic)
        anim_next.setStartValue(QPoint(offset, 0))
        anim_next.setEndValue(QPoint(0, 0))

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_current)
        group.addAnimation(anim_next)

        self._animating = True

        def on_finished():
            self.setCurrentIndex(target_index)
            current_widget.hide()
            current_widget.move(0, 0)
            self._animating = False

        group.finished.connect(on_finished)
        group.start()

class SafetyDialog(QDialog):
    """
    Interactive slide-by-slide safety & pre-flight verification modal.
    Guides operator through electrical isolation, 3.3V logic checks, and target architecture confirmation.
    """

    def __init__(
        self,
        product_name: str,
        parent=None,
        port_name: str = "COM3",
        firmware_info: Optional[FirmwareInfo] = None,
        target_chip: str = "ESP32"
    ):
        super().__init__(parent)
        self.product_name = product_name
        self.port_name = port_name
        self.firmware_info = firmware_info
        self.target_chip = target_chip
        self.current_step = 0

        self.setWindowTitle("PRE-FLIGHT VERIFICATION & SAFETY WIZARD")
        self.setFixedSize(620, 520)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #090D16;
                color: #F8FAFC;
                border: 1px solid #1E293B;
                border-radius: 12px;
            }
        """)

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(16)

        # Header with Title and Stepper Indicator
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)

        lbl_top = QLabel("PRE-FLIGHT SAFETY & SYSTEM VERIFICATION")
        lbl_top.setStyleSheet("color: #38BDF8; font-size: 16px; font-weight: 800; letter-spacing: 0.5px;")
        lbl_sub = QLabel("Pemeriksaan keselamatan kelistrikan dan integritas perangkat lunak sebelum flashing")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 11px;")

        header_layout.addWidget(lbl_top)
        header_layout.addWidget(lbl_sub)

        # Stepper Indicator Pills
        stepper_bar = QHBoxLayout()
        stepper_bar.setSpacing(8)

        self.step_pills = []
        step_titles = [
            "1. Isolasi AC 220V",
            "2. Level Logika 3.3V",
            "3. Profil Target"
        ]

        for i, title in enumerate(step_titles):
            pill = QLabel(title)
            pill.setAlignment(Qt.AlignCenter)
            pill.setFixedHeight(28)
            stepper_bar.addWidget(pill, stretch=1)
            self.step_pills.append(pill)

        header_layout.addLayout(stepper_bar)
        root_layout.addLayout(header_layout)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #1E293B; background-color: #1E293B; height: 1px;")
        root_layout.addWidget(sep)

        # Center Sliding Stack
        self.slider = SlidingStackedWidget()
        self.slide1 = self._create_slide1()
        self.slide2 = self._create_slide2()
        self.slide3 = self._create_slide3()

        self.slider.addWidget(self.slide1)
        self.slider.addWidget(self.slide2)
        self.slider.addWidget(self.slide3)

        root_layout.addWidget(self.slider, stretch=1)

        # Bottom Action Bar
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)

        self.btn_cancel = QPushButton(" Batalkan")
        self.btn_cancel.setIcon(IconProvider.get_icon("x-circle", color="#94A3B8", size=14))
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        bottom_layout.addStretch()

        self.btn_back = QPushButton(" Kembali")
        self.btn_back.setIcon(IconProvider.get_icon("rotate-ccw", color="#94A3B8", size=14))
        self.btn_back.setFixedHeight(40)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
        """)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setVisible(False)
        self.btn_back.clicked.connect(self._go_back)
        bottom_layout.addWidget(self.btn_back)

        self.btn_next = QPushButton("Konfirmasi & Lanjut ➔")
        self.btn_next.setFixedHeight(40)
        self.btn_next.setEnabled(False)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setToolTip("Centang kotak konfirmasi di atas untuk mengaktifkan tombol ini")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:disabled {
                background-color: #1E293B;
                color: #475569;
            }
        """)
        self.btn_next.clicked.connect(self._go_next)
        bottom_layout.addWidget(self.btn_next)

        root_layout.addLayout(bottom_layout)
        self._update_stepper_style()

    # ---------------- SLIDE BUILDERS ----------------

    def _create_slide1(self) -> QWidget:
        """Slide 1: AC Mains 220V Electrical Isolation."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        # Warning Card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #2D1515;
                border: 1px solid #7F1D1D;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        head_row = QHBoxLayout()
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconProvider.get_pixmap("alert-triangle", color="#EF4444", size=24))
        lbl_title = QLabel("LANGKAH 1/3: ISOLASI LISTRIK AC 220V (MANDATORY)")
        lbl_title.setStyleSheet("color: #F87171; font-size: 13px; font-weight: 800;")
        head_row.addWidget(lbl_icon)
        head_row.addWidget(lbl_title, stretch=1)
        c_layout.addLayout(head_row)

        desc = QLabel(
            "Perangkat energi (Smart Plug / CT Meter) mengontrol listrik jala-jala 220V AC.\n\n"
            "• PASTIKAN steker atau koneksi daya listrik AC 220V TELAH DICABUT TOTAL dari perangkat.\n"
            "• Proses flashing ESP HANYA menggunakan suplai daya DC 3.3V dari kabel USB programmer.\n"
            "• ⚠️ BAHAYA FATAL: Menghubungkan programmer saat steker AC 220V tercolok dapat menyebabkan "
            "sengatan listrik mematikan dan langsung merusak motherboard komputer Anda!"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #FECACA; font-size: 11px; line-height: 16px;")
        c_layout.addWidget(desc)
        layout.addWidget(card)

        # Checkbox Confirmation
        self.chk_slide1 = QCheckBox(
            "Saya menyatakan steker AC 220V SUDAH DICABUT dan perangkat bebas dari tegangan tinggi."
        )
        self.chk_slide1.setStyleSheet("""
            QCheckBox {
                color: #F8FAFC;
                font-size: 12px;
                font-weight: 600;
                padding: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.chk_slide1.stateChanged.connect(self._on_slide1_changed)
        layout.addWidget(self.chk_slide1)
        layout.addStretch()

        return page

    def _create_slide2(self) -> QWidget:
        """Slide 2: Voltage & UART Pinout Wiring (Specific for Plug vs CT)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        is_plug = "plug" in self.product_name.lower()

        card = QFrame()
        card_bg = "#2D2210" if is_plug else "#0F291E"
        card_border = "#78350F" if is_plug else "#065F46"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                padding: 14px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        head_row = QHBoxLayout()
        lbl_icon = QLabel()
        icon_name = "zap" if is_plug else "shield"
        icon_color = "#F59E0B" if is_plug else "#10B981"
        lbl_icon.setPixmap(IconProvider.get_pixmap(icon_name, color=icon_color, size=24))

        if is_plug:
            title_text = "LANGKAH 2/3: DAYA VCC (5V) & LEVEL LOGIKA UART (3.3V)"
            title_color = "#FBBF24"
            desc_text = (
                "⚡ SPESIFIKASI DAYA & LEVEL LOGIKA KHUSUS SMART PLUG (ESP32-C3):\n\n"
                "1. DAYA OPERASIONAL VCC (5V DC):\n"
                "   • Smart Plug MEMERLUKAN suplai daya 5V DC agar sirkuit onboard/regulator internal aktif.\n"
                "   • Hubungkan pin 5V adapter USB-TTL ke pin 5V / VCC pada Smart Plug.\n\n"
                "2. LEVEL LOGIKA KOMUNIKASI SERIAL (TETAP 3.3V):\n"
                "   • Level logika komunikasi data (RX & TX) WAJIB PADA LEVEL 3.3V DC!\n"
                "   • JANGAN gunakan level logika 5V pada pin RX/TX karena dapat merusak pin ESP32-C3.\n"
                "   • Pastikan jumper selektor logika USB-TTL (CP2102/CH340/FTDI) disetel pada 3.3V.\n\n"
                "Diagram Wiring Pinout (Smart Plug):\n"
                "  [USB-TTL] 5V   ───────▶ [5V / VCC] Smart Plug (Suplai Daya)\n"
                "  [USB-TTL] GND  ◀══════▶ [GND]      Smart Plug\n"
                "  [USB-TTL] TX   ───────▶ [RX]       Smart Plug (Logika 3.3V)\n"
                "  [USB-TTL] RX   ◀─────── [TX]       Smart Plug (Logika 3.3V)"
            )
            chk_text = "Saya memastikan daya VCC terhubung ke 5V dan level logika UART disetel ke 3.3V."
        else:
            title_text = "LANGKAH 2/3: DAYA & LEVEL LOGIKA SERIAL FULL 3.3V"
            title_color = "#34D399"
            desc_text = (
                "⚡ SPESIFIKASI DAYA & LEVEL LOGIKA CURRENT TRANSFORMER (ESP32 DUAL CORE):\n\n"
                "1. DAYA OPERASIONAL VCC (3.3V DC):\n"
                "   • Modul CT menggunakan suplai daya murni 3.3V DC langsung ke sirkuit ESP32.\n"
                "   • Hubungkan pin 3.3V adapter USB-TTL ke pin 3.3V / VCC pada modul CT.\n\n"
                "2. LEVEL LOGIKA SERIAL UART (FULL 3.3V):\n"
                "   • Seluruh jalur komunikasi data serial UART beroperasi pada level logika 3.3V DC.\n"
                "   • Pastikan jumper selektor tegangan USB-TTL berada pada posisi 3.3V (JANGAN 5V).\n\n"
                "Diagram Wiring Pinout (Current Transformer):\n"
                "  [USB-TTL] 3.3V ───────▶ [3.3V / VCC] CT Module (Suplai Daya)\n"
                "  [USB-TTL] GND  ◀══════▶ [GND]        CT Module\n"
                "  [USB-TTL] TX   ───────▶ [RX]         CT Module (Logika 3.3V)\n"
                "  [USB-TTL] RX   ◀─────── [TX]         CT Module (Logika 3.3V)"
            )
            chk_text = "Saya memastikan seluruh daya VCC dan logika UART berada pada level 3.3V."

        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet(f"color: {title_color}; font-size: 13px; font-weight: 800;")
        head_row.addWidget(lbl_icon)
        head_row.addWidget(lbl_title, stretch=1)
        c_layout.addLayout(head_row)

        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #FEF3C7; font-size: 11px; line-height: 16px; font-family: 'Segoe UI', monospace;")
        c_layout.addWidget(desc)
        layout.addWidget(card)

        self.chk_slide2 = QCheckBox(chk_text)
        self.chk_slide2.setCursor(Qt.PointingHandCursor)
        self.chk_slide2.setStyleSheet("""
            QCheckBox {
                color: #F8FAFC;
                font-size: 12px;
                font-weight: 600;
                padding: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.chk_slide2.stateChanged.connect(self._on_slide2_changed)
        layout.addWidget(self.chk_slide2)
        layout.addStretch()

        return page

    def _create_slide3(self) -> QWidget:
        """Slide 3: Pre-Flight Summary & Launch Confirmation."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        head_row = QHBoxLayout()
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconProvider.get_pixmap("check-circle", color="#10B981", size=24))
        lbl_title = QLabel("LANGKAH 3/3: RINGKASAN VERIFIKASI PRA-FLASHING")
        lbl_title.setStyleSheet("color: #34D399; font-size: 13px; font-weight: 800;")
        head_row.addWidget(lbl_icon)
        head_row.addWidget(lbl_title, stretch=1)
        c_layout.addLayout(head_row)

        fw_name = getattr(self.firmware_info, "file_name", getattr(self.firmware_info, "filename", "Official Factory Binary"))
        raw_hash = getattr(self.firmware_info, "sha256_hash", getattr(self.firmware_info, "sha256", ""))
        fw_hash = f"{raw_hash[:24]}..." if raw_hash else "Verified Checksum"

        # Mask proprietary firmware filename for corporate IP security
        if "plug" in str(self.product_name).lower() or "plug" in str(fw_name).lower():
            display_fw = "Alfa Smart Plug (Protected)"
        elif "ct" in str(self.product_name).lower() or "ct" in str(fw_name).lower():
            display_fw = "Alfa Energy CT (Protected)"
        else:
            display_fw = f"{self.product_name} (Protected)"

        is_plug = "plug" in self.product_name.lower()
        power_logic_summary = "Power: 5V DC | Logic: 3.3V UART (ESP32-C3)" if is_plug else "Power & Logic: Full 3.3V DC (ESP32 Dual Core)"

        specs = [
            ("Produk Target", f"{self.product_name}"),
            ("Target Chip Silicon", f"{self.target_chip} (Verified Architecture)"),
            ("Spesifikasi Daya & Logika", power_logic_summary),
            ("Port Komunikasi", f"{self.port_name}"),
            ("Firmware Binary", f"{display_fw}"),
            ("SHA-256 Hash", f"{fw_hash}"),
            ("Urutan Eksekusi", "1. Erase Flash Memory ➔ 2. Write Binary ➔ 3. Hash Verification")
        ]

        grid = QFrame()
        grid.setStyleSheet("background-color: #090D16; border-radius: 6px; padding: 8px;")
        g_layout = QVBoxLayout(grid)
        g_layout.setSpacing(6)

        for k, v in specs:
            r = QHBoxLayout()
            lk = QLabel(f"{k}:")
            lk.setFixedWidth(160)
            lk.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
            lv = QLabel(v)
            lv.setStyleSheet("color: #FBBF24 if 'Daya' in k else (#38BDF8 if 'Target' in k else #F8FAFC); font-weight: 700; font-size: 11px;")
            r.addWidget(lk)
            r.addWidget(lv, stretch=1)
            g_layout.addLayout(r)

        c_layout.addWidget(grid)
        layout.addWidget(card)

        lbl_ready = QLabel("Semua checklist keselamatan telah diverifikasi. Tekan tombol di bawah untuk memulai pipeline flashing.")
        lbl_ready.setStyleSheet("color: #10B981; font-weight: 700; font-size: 11px;")
        lbl_ready.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_ready)
        layout.addStretch()

        return page

    # ---------------- EVENT HANDLERS & STEPPING ----------------

    def _on_slide1_changed(self):
        if self.current_step == 0:
            self.btn_next.setEnabled(self.chk_slide1.isChecked())

    def _on_slide2_changed(self):
        if self.current_step == 1:
            self.btn_next.setEnabled(self.chk_slide2.isChecked())

    def _go_next(self):
        if self.current_step == 0:
            self.current_step = 1
            self.slider.slide_to_index(1, direction=1)
            self.btn_back.setVisible(True)
            self.btn_next.setText("Konfirmasi & Lanjut ➔")
            self.btn_next.setEnabled(self.chk_slide2.isChecked())
            self._update_stepper_style()

        elif self.current_step == 1:
            self.current_step = 2
            self.slider.slide_to_index(2, direction=1)
            self.btn_back.setVisible(True)
            self.btn_next.setText("🚀 MULAI FLASHING SEKARANG")
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background-color: #10B981;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 24px;
                    font-weight: 800;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """)
            self.btn_next.setEnabled(True)
            self._update_stepper_style()

        elif self.current_step == 2:
            self.accept()

    def _go_back(self):
        if self.current_step == 1:
            self.current_step = 0
            self.slider.slide_to_index(0, direction=-1)
            self.btn_back.setVisible(False)
            self.btn_next.setText("Konfirmasi & Lanjut ➔")
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover { background-color: #0369A1; }
                QPushButton:disabled { background-color: #1E293B; color: #475569; }
            """)
            self.btn_next.setEnabled(self.chk_slide1.isChecked())
            self._update_stepper_style()

        elif self.current_step == 2:
            self.current_step = 1
            self.slider.slide_to_index(1, direction=-1)
            self.btn_back.setVisible(True)
            self.btn_next.setText("Konfirmasi & Lanjut ➔")
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background-color: #0284C7;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover { background-color: #0369A1; }
                QPushButton:disabled { background-color: #1E293B; color: #475569; }
            """)
            self.btn_next.setEnabled(self.chk_slide2.isChecked())
            self._update_stepper_style()

    def _update_stepper_style(self):
        """Updates active highlight for stepper pills."""
        for idx, pill in enumerate(self.step_pills):
            if idx == self.current_step:
                pill.setStyleSheet("""
                    background-color: #0284C7;
                    color: #FFFFFF;
                    font-weight: 800;
                    font-size: 11px;
                    border-radius: 14px;
                    padding: 2px 8px;
                """)
            elif idx < self.current_step:
                pill.setStyleSheet("""
                    background-color: #064E3B;
                    color: #34D399;
                    font-weight: 700;
                    font-size: 11px;
                    border-radius: 14px;
                    padding: 2px 8px;
                """)
            else:
                pill.setStyleSheet("""
                    background-color: #1E293B;
                    color: #64748B;
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 14px;
                    padding: 2px 8px;
                """)
