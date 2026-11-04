"""
SpartaFlash - Cute Error 504 Offline Screen Overlay Component (Option B: Autonomous Zero-Click).
Developer: Rohidfkra777

Delightful playful offline screen displayed when the workstation detects no internet
connectivity during authentication. Features automatic background radar scanning,
zero required button clicks, instant network recovery, and clean titlebar close support.
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
    curious glances, and an animated dangling power plug.
    When connected, antenna and eyes illuminate in emerald green (^ ^).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 105)
        self._tick = 0.0
        self._blink = False
        self._look_dir = 0.0
        self._is_connected = False

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(33)  # ~30 FPS
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start()

    def set_connected(self, connected: bool = True):
        self._is_connected = connected
        self.update()

    def _on_tick(self):
        self._tick += 0.05
        # Eye blinking logic: blink briefly every ~3.5 seconds
        cycle = int(self._tick * 10) % 70
        self._blink = (cycle == 40 or cycle == 41)

        # Eye glancing left and right looking for Wi-Fi when disconnected
        if not self._is_connected:
            if 15 < cycle < 35:
                self._look_dir = math.sin((cycle - 15) / 20 * math.pi) * 3.5
            elif 45 < cycle < 65:
                self._look_dir = -math.sin((cycle - 45) / 20 * math.pi) * 3.5
            else:
                self._look_dir = 0.0
        else:
            self._look_dir = 0.0

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Gentle floating hover
        float_y = math.sin(self._tick * 2.5) * 4.0
        center_x = self.width() / 2.0
        base_y = 50.0 + float_y

        # 1. Subtle shadow under robot
        shadow_w = 54.0 - float_y * 1.5
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(15, 23, 42, 140))
        painter.drawEllipse(QPointF(center_x, 94), shadow_w / 2.0, 5.0)

        # 2. Antenna with tiny radar ball
        ant_top_y = base_y - 42.0
        painter.setPen(QPen(QColor("#64748B"), 2.5, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(center_x, base_y - 28), QPointF(center_x, ant_top_y))

        # Antenna spark: Green when online, Red when disconnected
        spark_color = QColor("#10B981") if self._is_connected else QColor("#EF4444")
        painter.setBrush(spark_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(center_x, ant_top_y), 4.5, 4.5)

        # Disconnected or Connected signal arcs
        arc_pulse = (math.sin(self._tick * 4.0) + 1.0) / 2.0
        if self._is_connected:
            arc_color = QColor(16, 185, 129, int(110 + 120 * arc_pulse))
        else:
            arc_color = QColor(239, 68, 68, int(100 + 120 * arc_pulse))

        arc_pen = QPen(arc_color, 1.8, Qt.SolidLine, Qt.RoundCap)
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

        border_color = QColor("#34D399") if self._is_connected else QColor("#38BDF8")
        painter.strokePath(body_path, QPen(border_color, 2.0))

        # 4. Cute Screen Face (Inner dark visor)
        visor_path = QPainterPath()
        visor_path.addRoundedRect(body_rect_x + 6, body_rect_y + 8, body_w - 12, 28, 7, 7)
        painter.fillPath(visor_path, QColor("#0B1120"))

        # 5. Eyes
        eye_y = body_rect_y + 22.0
        eye_spacing = 11.0
        eye_left_x = center_x - eye_spacing + self._look_dir
        eye_right_x = center_x + eye_spacing + self._look_dir

        if self._is_connected:
            # Happy smiling eyes (^ ^)
            painter.setPen(QPen(QColor("#34D399"), 2.2, Qt.SolidLine, Qt.RoundCap))
            path_left = QPainterPath()
            path_left.moveTo(eye_left_x - 4, eye_y + 2)
            path_left.quadTo(eye_left_x, eye_y - 3, eye_left_x + 4, eye_y + 2)
            painter.drawPath(path_left)

            path_right = QPainterPath()
            path_right.moveTo(eye_right_x - 4, eye_y + 2)
            path_right.quadTo(eye_right_x, eye_y - 3, eye_right_x + 4, eye_y + 2)
            painter.drawPath(path_right)
        elif self._blink:
            # Closed eyes (cute happy slits)
            painter.setPen(QPen(QColor("#38BDF8"), 2.2, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(eye_left_x - 3, eye_y), QPointF(eye_left_x + 3, eye_y))
            painter.drawLine(QPointF(eye_right_x - 3, eye_y), QPointF(eye_right_x + 3, eye_y))
        else:
            # Round big eyes with sparkle shine
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#38BDF8"))
            painter.drawEllipse(QPointF(eye_left_x, eye_y), 4.2, 4.8)
            painter.drawEllipse(QPointF(eye_right_x, eye_y), 4.2, 4.8)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(eye_left_x + 1.2, eye_y - 1.5), 1.5, 1.5)
            painter.drawEllipse(QPointF(eye_right_x + 1.2, eye_y - 1.5), 1.5, 1.5)

        # 6. Cute small blushing cheeks (soft coral pink)
        painter.setPen(Qt.NoPen)
        cheek_color = QColor(244, 63, 94, 130) if self._is_connected else QColor(244, 63, 94, 90)
        painter.setBrush(cheek_color)
        painter.drawEllipse(QPointF(center_x - 17, eye_y + 5.5), 3.5, 2.0)
        painter.drawEllipse(QPointF(center_x + 17, eye_y + 5.5), 3.5, 2.0)

        # 7. Dangling Unplugged Cable on the side
        cable_start_x = body_rect_x + body_w
        cable_start_y = body_rect_y + 36.0
        cable_end_x = cable_start_x + 16.0 + math.sin(self._tick * 3.0) * 3.0
        cable_end_y = cable_start_y + 12.0 + math.cos(self._tick * 3.0) * 2.0

        painter.setPen(QPen(QColor("#64748B"), 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(cable_start_x, cable_start_y), QPointF(cable_end_x, cable_end_y))

        # Plug head (green when restored, red when disconnected)
        plug_color = QColor("#10B981") if self._is_connected else QColor("#EF4444")
        painter.setBrush(plug_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(int(cable_end_x), int(cable_end_y - 4), 9, 8, 2, 2)
        # Prongs
        painter.setPen(QPen(QColor("#CBD5E1"), 1.8, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(cable_end_x + 9, cable_end_y - 2), QPointF(cable_end_x + 13, cable_end_y - 2))
        painter.drawLine(QPointF(cable_end_x + 9, cable_end_y + 2), QPointF(cable_end_x + 13, cable_end_y + 2))


class CuteOfflineOverlay(QFrame):
    """
    Playful Error 504 Offline Screen overlay with animated mascot,
    live autonomous radar scanning (Option B - Zero Button), and auto-redirect.
    """
    def __init__(self, on_retry_callback: Callable[[], bool], on_back_callback: Callable[[], None], parent=None):
        super().__init__(parent)
        self.on_retry_callback = on_retry_callback
        self.on_back_callback = on_back_callback
        self._dots_step = 0

        self.setStyleSheet("""
            QFrame {
                background-color: #0B1120;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Animated Mascot
        self.mascot = CuteMascotWidget(self)
        mascot_box = QHBoxLayout()
        mascot_box.setAlignment(Qt.AlignCenter)
        mascot_box.addWidget(self.mascot)
        layout.addLayout(mascot_box)
        layout.addSpacing(6)

        # 2. Big 504 Code
        lbl_code = QLabel("ERROR 504")
        lbl_code.setAlignment(Qt.AlignCenter)
        lbl_code.setStyleSheet("""
            color: #EF4444;
            font-size: 20px;
            font-weight: 900;
            letter-spacing: 1.5px;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        """)
        layout.addWidget(lbl_code)
        layout.addSpacing(4)

        # 3. Friendly Headline
        lbl_title = QLabel("Sinyal Kabur Nih! 📡")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("""
            color: #F8FAFC;
            font-size: 13.5px;
            font-weight: 800;
            letter-spacing: 0.3px;
        """)
        layout.addWidget(lbl_title)
        layout.addSpacing(6)

        # 4. Description
        lbl_desc = QLabel(
            "Workstation mendeteksi kabel LAN lepas atau Wi-Fi lagi ngambek.\n"
            "Sambungkan internet stasiun agar kredensial dapat diverifikasi."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("""
            color: #94A3B8;
            font-size: 10.5px;
            line-height: 140%;
            font-weight: 500;
        """)
        layout.addWidget(lbl_desc)
        layout.addSpacing(16)

        # 5. Live Auto-Scanning Radar Badge (Zero Buttons Design)
        self.frame_scanner = QFrame()
        self.frame_scanner.setObjectName("frameRadarScanner")
        self.frame_scanner.setFixedHeight(46)
        self.frame_scanner.setStyleSheet("""
            QFrame#frameRadarScanner {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        scan_l = QHBoxLayout(self.frame_scanner)
        scan_l.setContentsMargins(14, 8, 14, 8)
        scan_l.setSpacing(10)

        self.lbl_radar_icon = QLabel("📡")
        self.lbl_radar_icon.setStyleSheet("font-size: 16px;")
        scan_l.addWidget(self.lbl_radar_icon)

        self.lbl_scanner_status = QLabel("Memindai sinyal internet stasiun...")
        self.lbl_scanner_status.setStyleSheet("""
            color: #38BDF8;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.2px;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        """)
        scan_l.addWidget(self.lbl_scanner_status, stretch=1)
        layout.addWidget(self.frame_scanner)
        layout.addSpacing(12)

        # 6. Escape Hatch Micro-Hint
        lbl_hint = QLabel("Aplikasi otomatis kembali ke login saat terhubung  •  Tekan Esc / [X] untuk keluar")
        lbl_hint.setAlignment(Qt.AlignCenter)
        lbl_hint.setStyleSheet("color: #64748B; font-size: 9px; font-weight: 500;")
        layout.addWidget(lbl_hint)

        # Hidden programmatic buttons preserved for test / API backward compatibility
        self.btn_back = QPushButton("Kembali")
        self.btn_back.setVisible(False)
        self.btn_back.clicked.connect(self.on_back_callback)

        self.btn_retry = QPushButton("Coba Sambungkan Lagi")
        self.btn_retry.setVisible(False)
        self.btn_retry.clicked.connect(self._trigger_retry)

        # Pulse Dots Timer for Live Scanning
        self._dots_timer = QTimer(self)
        self._dots_timer.setInterval(450)
        self._dots_timer.timeout.connect(self._on_dots_tick)
        self._dots_timer.start()

    def _on_dots_tick(self):
        if self.mascot._is_connected:
            return
        self._dots_step = (self._dots_step + 1) % 4
        dots = "." * self._dots_step
        self.lbl_scanner_status.setText(f"Memindai sinyal internet stasiun{dots}")

    def show_connected_success(self):
        """Displays connected state with vibrant emerald theme before auto-redirecting."""
        if hasattr(self, "_dots_timer"):
            self._dots_timer.stop()
        self.mascot.set_connected(True)
        self.lbl_radar_icon.setText("⚡")
        self.lbl_scanner_status.setText("Internet Terhubung! Mengalihkan ke login...")
        self.lbl_scanner_status.setStyleSheet("""
            color: #34D399;
            font-size: 11.5px;
            font-weight: 800;
            letter-spacing: 0.3px;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        """)
        self.frame_scanner.setStyleSheet("""
            QFrame#frameRadarScanner {
                background-color: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 8px;
            }
        """)

    def reset_state(self):
        """Resets feedback and radar scanner state when overlay becomes visible."""
        self.mascot.set_connected(False)
        self.lbl_radar_icon.setText("📡")
        self.lbl_scanner_status.setText("Memindai sinyal internet stasiun...")
        self.lbl_scanner_status.setStyleSheet("""
            color: #38BDF8;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.2px;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        """)
        self.frame_scanner.setStyleSheet("""
            QFrame#frameRadarScanner {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        if hasattr(self, "_dots_timer") and not self._dots_timer.isActive():
            self._dots_timer.start()

    def _trigger_retry(self):
        if self.on_retry_callback:
            online = self.on_retry_callback()
            if online:
                self.show_connected_success()
                QTimer.singleShot(600, self.on_back_callback)
