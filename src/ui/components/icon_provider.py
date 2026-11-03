"""
SpartaFlash - Lucide Vector Icon Provider for Qt.
Developer: Rohidfkra777

Provides crisp, scalable, dynamically tinted vector icons from Lucide SVG templates.
"""

from pathlib import Path
from typing import Optional, Dict
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt, QByteArray, QSize
from src.config.constants import ASSETS_DIR

ICONS_DIR = ASSETS_DIR / "icons"

class IconProvider:
    """Manages Lucide vector icons with dynamic color tinting and in-memory caching."""

    _cache: Dict[str, QIcon] = {}
    _pixmap_cache: Dict[str, QPixmap] = {}
    _svg_templates: Dict[str, str] = {}

    @classmethod
    def _get_svg_template(cls, icon_name: str) -> Optional[str]:
        if icon_name in cls._svg_templates:
            return cls._svg_templates[icon_name]

        # Check in ASSETS_DIR / icons or root assets/icons
        candidates = [
            ICONS_DIR / f"{icon_name}.svg",
            Path("assets/icons") / f"{icon_name}.svg",
            ICONS_DIR.parent.parent / "assets" / "icons" / f"{icon_name}.svg",
        ]

        for p in candidates:
            if p.exists():
                try:
                    content = p.read_text(encoding="utf-8")
                    cls._svg_templates[icon_name] = content
                    return content
                except Exception:
                    pass

        return None

    @classmethod
    def get_pixmap(cls, icon_name: str, color: str = "#F8FAFC", size: int = 20) -> QPixmap:
        """Returns a tinted QPixmap of the requested Lucide icon."""
        cache_key = f"{icon_name}_{color}_{size}"
        if cache_key in cls._pixmap_cache:
            return cls._pixmap_cache[cache_key]

        template = cls._get_svg_template(icon_name)
        if not template:
            pix = QPixmap(size, size)
            pix.fill(Qt.transparent)
            return pix

        # Replace currentColor with target hex color
        svg_colored = template.replace('stroke="currentColor"', f'stroke="{color}"')
        renderer = QSvgRenderer(QByteArray(svg_colored.encode("utf-8")))

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        cls._pixmap_cache[cache_key] = pixmap
        return pixmap

    @classmethod
    def get_icon(
        cls,
        icon_name: str,
        color: str = "#94A3B8",
        active_color: Optional[str] = "#38BDF8",
        disabled_color: str = "#475569",
        size: int = 20
    ) -> QIcon:
        """
        Creates a multi-state QIcon for QPushButton / QAction.
        Normal, Active/Selected, and Disabled states are colored automatically.
        """
        cache_key = f"icon_{icon_name}_{color}_{active_color}_{disabled_color}_{size}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        icon = QIcon()

        # Normal State
        pix_normal = cls.get_pixmap(icon_name, color=color, size=size)
        icon.addPixmap(pix_normal, QIcon.Normal, QIcon.Off)

        # Active / Selected State
        if active_color:
            pix_active = cls.get_pixmap(icon_name, color=active_color, size=size)
            icon.addPixmap(pix_active, QIcon.Active, QIcon.Off)
            icon.addPixmap(pix_active, QIcon.Normal, QIcon.On)

        # Disabled State
        if disabled_color:
            pix_disabled = cls.get_pixmap(icon_name, color=disabled_color, size=size)
            icon.addPixmap(pix_disabled, QIcon.Disabled, QIcon.Off)

        cls._cache[cache_key] = icon
        return icon
