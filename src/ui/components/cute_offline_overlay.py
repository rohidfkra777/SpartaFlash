"""
SpartaFlash - Cute Error 504 Offline Screen Overlay Component.
Developer: Rohidfkra777

Delightful playful offline screen displayed when the workstation detects no internet
connectivity during authentication or network barrier enforcement.
"""

import math
from typing import Callable, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath


class CuteMascotWidget(QWidget):
    """
    Cute animated offline robot/terminal with floating bob, blinking eyes,
    curious glances, and a dangling disconnected power plug.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 110)
        self._tick = 0.0
        self._blink = False
        self._look_dir = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(33)  # ~30 FPS
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start()

    def _on_tick(self):
        self._tick += 0.05
        # Eye blinking logic: blink briefly every ~3.5 seconds
        cycle = int(self._tick * 10) % 70
        self._blink = (cycle == 40 or cycle == 41)

        # Eye glancing left and right looking for Wi-Fi
        if 15 < cycle < 35:
            self._look_dir = math.sin((cycle - 15) / 20 * math.pi) * 3.5
        elif 45 < cycle < 65:
            self._look_dir = -math.sin((cycle - 45) / 20 * math.pi) * 3.5
        else:
            self._look_dir = 0.0

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Gentle floating hover
        float_y = math.sin(self._tick * 2.5) * 4.0
        center_x = self.width() / 2.0
        base_y = 52.0 + float_y

        # 1. Subtle shadow under robot
        shadow_w = 54.0 - float_y * 1.5
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(15, 23, 42, 140))
        painter.drawEllipse(QPointF(center_x, 96), shadow_w / 2.0, 5.0)

        # 2. Antenna with tiny radar ball
        ant_top_y = base_y - 42.0
        painter.setPen(QPen(QColor("#64748B"), 2.5, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(center_x, base_y - 28), QPointF(center_x, ant_top_y))

        # Antenna spark / disconnected signal
        painter.setBrush(QColor("#EF4444"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(center_x, ant_top_y), 4.5, 4.5)

        # Disconnected signal arcs (faint red)
        arc_pulse = (math.sin(self._tick * 4.0) + 1.0) / 2.0
        arc_pen = QPen(QColor(239, 68, 68, int(100 + 120 * arc_pulse)), 1.8, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(arc_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(int(center_x - 12), int(ant_top_y - 12), 24, 24, 45 * 16, 90 * 16)
        painter.drawArc(int(center_x - 18), int(ant_top_y - 18), 36, 36, 50 * 16, 80 * 16)

        # 3. Cute Robot Body (Rounded box)
        body_rect_x = center_x - 30.0
        body_rect_y = base_y - 28.0
        body_w = 60.0
        body_h = 48.0

        body_path = QPainterPath()
        body_path.addRoundedRect(body_rect_x, body_rect_y, body_w, body_h, 12, 12)
        painter.fillPath(body_path, QColor("#1E293B"))
        painter.strokePath(body_path, QPen(QColor("#38BDF8"), 2.0))

        # 4. Cute Screen Face (Inner dark visor)
        visor_path = QPainterPath()
        visor_path.addRoundedRect(body_rect_x + 6, body_rect_y + 8, body_w - 12, 28, 7, 7)
        painter.fillPath(visor_path, QColor("#0B1120"))

        # 5. Eyes (Cute expressive cyan dots or blinking happy slits)
        eye_y = body_rect_y + 22.0
        eye_spacing = 11.0
        eye_left_x = center_x - eye_spacing + self._look_dir
        eye_right_x = center_x + eye_spacing + self._look_dir

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#38BDF8"))

        if self._blink:
            # Closed eyes (cute happy slits)
            painter.setPen(QPen(QColor("#38BDF8"), 2.2, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(eye_left_x - 3, eye_y), QPointF(eye_left_x + 3, eye_y))
            painter.drawLine(QPointF(eye_right_x - 3, eye_y), QPointF(eye_right_x + 3, eye_y))
        else:
            # Round big eyes with sparkle shine
            painter.drawEllipse(QPointF(eye_left_x, eye_y), 4.2, 4.8)
            painter.drawEllipse(QPointF(eye_right_x, eye_y), 4.2, 4.8)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(eye_left_x + 1.2, eye_y - 1.5), 1.5, 1.5)
            painter.drawEllipse(QPointF(eye_right_x + 1.2, eye_y - 1.5), 1.5, 1.5)

        # 6. Cute small blushing cheeks (soft coral pink)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(244, 63, 94, 90))
        painter.drawEllipse(QPointF(center_x - 17, eye_y + 5.5), 3.5, 2.0)
        painter.drawEllipse(QPointF(center_x + 17, eye_y + 5.5), 3.5, 2.0)

        # 7. Dangling Unplugged Cable on the side
        cable_start_x = body_rect_x + body_w
        cable_start_y = body_rect_y + 36.0
        cable_end_x = cable_start_x + 16.0 + math.sin(self._tick * 3.0) * 3.0
        cable_end_y = cable_start_y + 12.0 + math.cos(self._tick * 3.0) * 2.0

        painter.setPen(QPen(QColor("#64748B"), 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(cable_start_x, cable_start_y), QPointF(cable_end_x, cable_end_y))

        # Plug head
        painter.setBrush(QColor("#EF4444"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(int(cable_end_x), int(cable_end_y - 4), 9, 8, 2, 2)
        # Prongs
        painter.setPen(QPen(QColor("#CBD5E1"), 1.8, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(cable_end_x + 9, cable_end_y - 2), QPointF(cable_end_x + 13, cable_end_y - 2))
        painter.drawLine(QPointF(cable_end_x + 9, cable_end_y + 2), QPointF(cable_end_x + 13, cable_end_y + 2))


class CuteOfflineOverlay(QFrame):
    """
    Playful Error 504 Offline Screen overlay with animated mascot,
    status details, and interactive retry / return controls.
    """
    def __init__(self, on_retry_callback: Callable[[], bool], on_back_callback: Callable[[], None], parent=None):
        super().__init__(parent)
        self.on_retry_callback = on_retry_callback
        self.on_back_callback = on_back_callback

        self.setStyleSheet("""
            QFrame {
                background-color: #0B1120;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Animated Mascot
        self.mascot = CuteMascotWidget(self)
        mascot_box = QHBoxLayout()
        mascot_box.setAlignment(Qt.AlignCenter)
        mascot_box.addWidget(self.mascot)
        layout.addLayout(mascot_box)
        layout.addSpacing(6)

        # 2. Big 504 Code Pill
        code_box = QHBoxLayout()
        code_box.setAlignment(Qt.AlignCenter)

        lbl_code = QLabel("ERROR 504")
        lbl_code.setAlignment(Qt.AlignCenter)
        lbl_code.setStyleSheet("""
            color: #EF4444;
            font-size: 22px;
            font-weight: 900;
            letter-spacing: 1.5px;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        """)
        code_box.addWidget(lbl_code)
        layout.addLayout(code_box)
        layout.addSpacing(4)

        # 3. Funny Catchy Headline
        lbl_title = QLabel("Sinyal Kabur Nih! 📡")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("""
            color: #F8FAFC;
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.3px;
        """)
        layout.addWidget(lbl_title)
        layout.addSpacing(6)

        # 4. Friendly Subtitle
        lbl_desc = QLabel(
            "Workstation mendeteksi kabel LAN lepas atau Wi-Fi lagi ngambek.\n"
            "Sambungkan internet stasiun agar kredensial dapat diverifikasi."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("""
            color: #94A3B8;
            font-size: 11px;
            line-height: 140%;
            font-weight: 500;
        """)
        layout.addWidget(lbl_desc)
        layout.addSpacing(18)

        # 5. Status Feedback Label (when testing)
        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setAlignment(Qt.AlignCenter)
        self.lbl_feedback.setFixedHeight(18)
        self.lbl_feedback.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: 700;")
        layout.addWidget(self.lbl_feedback)
        layout.addSpacing(10)

        # 6. Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_back = QPushButton("Kembali")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setFixedHeight(38)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """)
        self.btn_back.clicked.connect(self.on_back_callback)
        btn_box.addWidget(self.btn_back)

        self.btn_retry = QPushButton("🔄 Coba Sambungkan Lagi")
        self.btn_retry.setCursor(Qt.PointingHandCursor)
        self.btn_retry.setFixedHeight(38)
        self.btn_retry.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1);
                color: #FFFFFF;
                border: 1px solid #38BDF8;
                border-radius: 6px;
                padding: 0 18px;
                font-weight: 700;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #0284C7);
            }
            QPushButton:disabled {
                background: #1E293B;
                color: #64748B;
                border: 1px solid #334155;
            }
        """)
        self.btn_retry.clicked.connect(self._trigger_retry)
        btn_box.addWidget(self.btn_retry, stretch=1)

        layout.addLayout(btn_box)

    def reset_state(self):
        """Resets feedback and button state when overlay becomes visible."""
        self.lbl_feedback.setText("")
        self.btn_retry.setEnabled(True)
        self.btn_retry.setText("🔄 Coba Sambungkan Lagi")

    def _trigger_retry(self):
        self.btn_retry.setEnabled(False)
        self.btn_retry.setText("⏳ Memeriksa Jaringan...")
        self.lbl_feedback.setText("Melakukan ping ke gateway stasiun...")
        self.lbl_feedback.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600;")
        QTimer.singleShot(600, self._perform_check)

    def _perform_check(self):
        if self.on_retry_callback:
            online = self.on_retry_callback()
            if online:
                self.lbl_feedback.setText("✅ Jaringan Terhubung! Kembali ke login...")
                self.lbl_feedback.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 800;")
                QTimer.singleShot(600, self.on_back_callback)
            else:
                self.btn_retry.setEnabled(True)
                self.btn_retry.setText("🔄 Coba Sambungkan Lagi")
                self.lbl_feedback.setText("Masih belum ada sinyal, periksa kabel lagi ya! 🔌")
                self.lbl_feedback.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 700;")

