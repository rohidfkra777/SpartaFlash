"""
SpartaFlash - Industrial Modern Dark Theme & QSS Styling.
Developer: Rohidfkra777

High-contrast, eye-friendly industrial dark theme designed for factory workstations:
- Canvas / Base: #0F172A (Deep Slate 900)
- Sidebar: #0B1120 (Slate 950) with border #1E293B
- Cards & Elevators: #1E293B (Slate 800) with crisp border #334155
- Primary Accent: #38BDF8 (Sky 400) / #0284C7 (Sky 600)
- Action Green: #10B981 (Emerald 500)
- Danger Red: #EF4444 (Red 500)
- Terminal Log: #090D16 (Ultra-dark terminal with Sky 400 monospace text)
"""

from src.config.constants import ASSETS_DIR

CHEVRON_ICON_PATH = (ASSETS_DIR / "icons" / "chevron-down.png").as_posix()
CHEVRON_HOVER_ICON_PATH = (ASSETS_DIR / "icons" / "chevron-down-hover.png").as_posix()
CHECK_ICON_PATH = (ASSETS_DIR / "icons" / "check-white.png").as_posix()

_BASE_INDUSTRIAL_DARK_QSS = """
/* Global Window & Typography */
QMainWindow, QWidget#centralWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Global Tooltip */
QToolTip {
    background-color: #0B1120;
    color: #F8FAFC;
    border: 1px solid #38BDF8;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 11px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    font-weight: 600;
}

/* Sidebar / Navigation */
QFrame#sidebarFrame {
    background-color: #0B1120;
    border-right: 1px solid #1E293B;
}

QLabel#appTitleLabel {
    color: #38BDF8;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QLabel#appSubtitleLabel {
    color: #94A3B8;
    font-size: 11px;
    font-weight: 600;
}

QLabel#miniLogoLabel {
    color: #38BDF8;
    font-size: 20px;
    font-weight: 900;
    padding: 2px 0;
}

/* Sidebar Toggle Buttons */
QPushButton#btnCollapseSidebar, QPushButton#btnToggleRail {
    background-color: #1E293B;
    color: #94A3B8;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 800;
    padding: 2px;
}

QPushButton#btnCollapseSidebar:hover, QPushButton#btnToggleRail:hover {
    background-color: #334155;
    color: #38BDF8;
    border: 1px solid #38BDF8;
}

QPushButton#btnExpandSidebar {
    background-color: #1E293B;
    color: #38BDF8;
    border: 1px solid #38BDF8;
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#btnExpandSidebar:hover {
    background-color: #0284C7;
    color: #FFFFFF;
}

/* Resizable Splitter */
QSplitter {
    background-color: transparent;
}

QSplitter::handle:horizontal {
    background-color: #1E293B;
    width: 6px;
    border-left: 1px solid #0F172A;
    border-right: 1px solid #334155;
}

QSplitter::handle:horizontal:hover {
    background-color: #38BDF8;
}

/* Sidebar Edge Toggle Handle Button (Triangle in Middle of Edge) */
QPushButton#btnSidebarEdgeToggle {
    background-color: #1E293B;
    color: #94A3B8;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    padding: 0;
    text-align: center;
}
QPushButton#btnSidebarEdgeToggle:hover {
    background-color: #334155;
    color: #38BDF8;
    border-color: #38BDF8;
}
QPushButton#btnSidebarEdgeToggle:pressed {
    background-color: #0F172A;
}


/* Navigation Buttons (Clean Workstation - Left Accent Indicator) */
QPushButton.nav-button {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}

QPushButton.nav-button[compact="true"] {
    text-align: center;
    padding: 8px 0px;
    font-size: 15px;
    border-radius: 6px;
}

QPushButton.nav-button:hover {
    background-color: #1E293B;
    color: #38BDF8;
}

QPushButton.nav-button:checked, QPushButton.nav-button[active="true"] {
    background-color: #1E293B;
    color: #38BDF8;
    border-left: 3px solid #38BDF8;
    border-radius: 6px;
    font-weight: 700;
}

QPushButton.nav-button[compact="true"]:checked, QPushButton.nav-button[compact="true"][active="true"] {
    background-color: #1E293B;
    color: #38BDF8;
    border-left: 3px solid #38BDF8;
    border-radius: 4px;
}

/* Cards & Containers */
QFrame.card, QFrame#statCard {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px;
}

QFrame.card-highlight {
    background-color: #1E293B;
    border: 1px solid #0284C7;
    border-radius: 10px;
}

QLabel.card-title {
    color: #E2E8F0;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

QLabel.card-subtitle {
    color: #94A3B8;
    font-size: 11px;
}

/* Controls: ComboBox, LineEdit, SpinBox */
QComboBox {
    background-color: #0F172A;
    border: 1.5px solid #475569;
    border-radius: 6px;
    padding: 7px 36px 7px 12px;
    color: #F8FAFC;
    font-size: 13px;
    selection-background-color: #0284C7;
    min-height: 22px;
}

QLineEdit, QSpinBox {
    background-color: #0F172A;
    border: 1.5px solid #475569;
    border-radius: 6px;
    padding: 7px 12px;
    color: #F8FAFC;
    font-size: 13px;
    selection-background-color: #0284C7;
}

QComboBox:hover, QLineEdit:hover, QSpinBox:hover {
    border: 1.5px solid #38BDF8;
    background-color: #131E33;
}

QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QComboBox:on {
    border: 1.5px solid #38BDF8;
    background-color: #131E33;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 32px;
    border-left: 1px solid #334155;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
    background-color: #1E293B;
}

QComboBox::drop-down:hover {
    background-color: #0284C7;
}

QComboBox::down-arrow {
    image: url("__CHEVRON_ICON__");
    width: 14px;
    height: 14px;
}

QComboBox::down-arrow:hover {
    image: url("__CHEVRON_HOVER_ICON__");
}

QComboBox QAbstractItemView {
    background-color: #0F172A;
    border: 1.5px solid #38BDF8;
    border-radius: 6px;
    color: #F8FAFC;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
    outline: none;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    min-height: 30px;
    padding: 4px 8px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #1E293B;
    color: #38BDF8;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #0284C7;
    color: #FFFFFF;
}

/* VIP Target Product Selector */
QComboBox#targetProductSelector {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0D192E, stop:1 #1A2942);
    border: 2px solid #38BDF8;
    border-radius: 8px;
    padding: 9px 48px 9px 14px;
    color: #FFFFFF;
    font-size: 13.5px;
    font-weight: 700;
    min-height: 26px;
}

QComboBox#targetProductSelector:hover {
    border: 2px solid #7DD3FC;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #12223F, stop:1 #223759);
}

QComboBox#targetProductSelector:focus, QComboBox#targetProductSelector:on {
    border: 2px solid #38BDF8;
    background-color: #142646;
}

QComboBox#targetProductSelector::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 42px;
    border-left: 2px solid #38BDF8;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0284C7, stop:1 #0369A1);
}

QComboBox#targetProductSelector::drop-down:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38BDF8, stop:1 #0284C7);
}

QComboBox#targetProductSelector::down-arrow {
    image: url("__CHEVRON_HOVER_ICON__");
    width: 16px;
    height: 16px;
}

QComboBox#targetProductSelector QAbstractItemView {
    background-color: #0B1120;
    border: 2px solid #38BDF8;
    border-radius: 8px;
    color: #F8FAFC;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
    padding: 6px;
}

QComboBox#targetProductSelector QAbstractItemView::item {
    min-height: 38px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
    border-radius: 6px;
}

QComboBox#targetProductSelector QAbstractItemView::item:hover {
    background-color: #1E293B;
    color: #38BDF8;
}

QComboBox#targetProductSelector QAbstractItemView::item:selected {
    background-color: #0284C7;
    color: #FFFFFF;
}

/* Primary Action Buttons */
QPushButton.btn-primary {
    background-color: #0284C7;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.btn-primary:hover {
    background-color: #0369A1;
}

QPushButton.btn-primary:pressed {
    background-color: #075985;
}

QPushButton.btn-primary:disabled {
    background-color: #334155;
    color: #64748B;
}

/* Big Action Flashing Button */
QPushButton#btnStartFlash {
    background-color: #10B981;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QPushButton#btnStartFlash:hover {
    background-color: #059669;
}

QPushButton#btnStartFlash:disabled {
    background-color: #334155;
    color: #64748B;
}

QPushButton#btnCancelFlash {
    background-color: #EF4444;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 15px;
    font-weight: 700;
}

QPushButton#btnCancelFlash:hover {
    background-color: #DC2626;
}

/* Secondary Button */
QPushButton.btn-secondary {
    background-color: #334155;
    color: #E2E8F0;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton.btn-secondary:hover {
    background-color: #475569;
    color: #FFFFFF;
}

/* Danger Action Button */
QPushButton.btn-danger {
    background-color: #7F1D1D;
    color: #F87171;
    border: 1px solid #DC2626;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton.btn-danger:hover {
    background-color: #991B1B;
    color: #FFFFFF;
    border-color: #EF4444;
}

QPushButton.btn-danger:pressed {
    background-color: #450A0A;
}

QPushButton.btn-danger:disabled {
    background-color: #1E293B;
    border-color: #334155;
    color: #64748B;
}

/* Status Badges */
QLabel.badge-pass {
    background-color: #064E3B;
    color: #34D399;
    border: 1px solid #059669;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 800;
    font-size: 11.5px;
    letter-spacing: 0.5px;
    qproperty-alignment: AlignCenter;
}

QLabel.badge-fail {
    background-color: #7F1D1D;
    color: #F87171;
    border: 1px solid #DC2626;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 800;
    font-size: 11.5px;
    letter-spacing: 0.5px;
    qproperty-alignment: AlignCenter;
}

QLabel.badge-ready {
    background-color: #064E3B;
    color: #34D399;
    border: 1px solid #10B981;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 800;
    font-size: 11.5px;
    letter-spacing: 0.5px;
    qproperty-alignment: AlignCenter;
}

QLabel.badge-running {
    background-color: #0C4A6E;
    color: #38BDF8;
    border: 1px solid #0284C7;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 800;
    font-size: 11.5px;
    letter-spacing: 0.5px;
    qproperty-alignment: AlignCenter;
}

QLabel.badge-warn {
    background-color: #78350F;
    color: #FBBF24;
    border: 1px solid #D97706;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 800;
    font-size: 11.5px;
    letter-spacing: 0.5px;
    qproperty-alignment: AlignCenter;
}

/* Progress Bar */
QProgressBar {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #F8FAFC;
    font-weight: 600;
    font-size: 12px;
    height: 22px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #10B981);
    border-radius: 5px;
}

/* Terminal Log View */
QPlainTextEdit#terminalLog {
    background-color: #090D16;
    color: #38BDF8;
    border: 1px solid #1E293B;
    border-radius: 8px;
    font-family: 'Cascadia Mono', 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
    selection-background-color: #0284C7;
}

/* Tables */
QTableWidget {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #1E293B;
    color: #F8FAFC;
    selection-background-color: #1E293B;
    selection-color: #38BDF8;
    alternate-background-color: #131E33;
    font-size: 11.5px;
}

QTableWidget::item {
    padding: 3px 6px;
}

QTableWidget::item:selected {
    background-color: #1E293B;
    color: #38BDF8;
}

QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    font-weight: 700;
    font-size: 11px;
    padding: 7px 8px;
    border: none;
    border-bottom: 2px solid #334155;
    border-right: 1px solid #1A2639;
}

/* ScrollBars */
QScrollBar:vertical {
    background-color: #0F172A;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #0F172A;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #334155;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #475569;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}


/* Checkboxes */
QCheckBox {
    color: #94A3B8;
    font-size: 12px;
    font-weight: 500;
    spacing: 7px;
}

QCheckBox:hover {
    color: #F8FAFC;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #334155;
    border-radius: 4px;
    background-color: #0F172A;
}

QCheckBox::indicator:hover {
    border-color: #38BDF8;
    background-color: #1E293B;
}

QCheckBox::indicator:checked {
    background-color: #0284C7;
    border-color: #38BDF8;
    image: url("__CHECK_ICON__");
}

QCheckBox::indicator:checked:hover {
    background-color: #0369A1;
    border-color: #7DD3FC;
    image: url("__CHECK_ICON__");
}

QCheckBox::indicator:disabled {
    border-color: #1E293B;
    background-color: #0B1120;
}

/* Footer */
QFrame#footerFrame {
    background-color: #0B1120;
    border-top: 1px solid #1E293B;
    padding: 4px 12px;
}

QLabel#footerLabel {
    color: #64748B;
    font-size: 11px;
}

QLabel#footerLink {
    color: #38BDF8;
    font-size: 11px;
    font-weight: 600;
}
"""

INDUSTRIAL_DARK_QSS = _BASE_INDUSTRIAL_DARK_QSS.replace("__CHEVRON_ICON__", CHEVRON_ICON_PATH).replace("__CHEVRON_HOVER_ICON__", CHEVRON_HOVER_ICON_PATH).replace("__CHECK_ICON__", CHECK_ICON_PATH)

# Alias for backwards compatibility with any imports
NEUMORPHISM_QSS = INDUSTRIAL_DARK_QSS

