"""
Topology Parser for AlfaEnergy Devices.
Handles parsing and formatting of device location/role convention:
  kodetoko/namapanel/fasa
Examples:
  - T105/MDP/R       -> 3-Phase Panel MDP, Phase R
  - T105/MDP/S       -> 3-Phase Panel MDP, Phase S
  - T105/MDP/T       -> 3-Phase Panel MDP, Phase T
  - T105/OVEN/1F     -> 1-Phase Heavy Load (Oven)
  - T105/SHOWCASE    -> 1-Phase Plug / Device
"""

from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class DeviceTopology:
    raw: str = ""
    store_code: str = ""
    panel_name: str = ""
    phase: Optional[str] = None  # "R", "S", "T", "1F", or None
    is_valid: bool = False
    is_three_phase: bool = False

    @property
    def phase_color(self) -> str:
        """Standard PUIL / electrical phase colors."""
        if self.phase == "R":
            return "#EF4444"  # Red (Phase R / L1)
        elif self.phase == "S":
            return "#EAB308"  # Yellow (Phase S / L2)
        elif self.phase == "T":
            return "#3B82F6"  # Blue (Phase T / L3)
        elif self.phase == "1F":
            return "#94A3B8"  # Slate/Gray (Single Phase)
        return "#38BDF8"      # Sky Blue (Generic / Default)

    @property
    def display_badge(self) -> str:
        if self.is_three_phase and self.phase:
            return f"[{self.phase}]"
        elif self.phase == "1F":
            return "[1F]"
        return ""

    @property
    def formatted_summary(self) -> str:
        if not self.is_valid:
            return self.raw
        if self.is_three_phase and self.phase:
            return f"{self.store_code}/{self.panel_name}/{self.phase}"
        elif self.phase == "1F":
            return f"{self.store_code}/{self.panel_name}/1F"
        return f"{self.store_code}/{self.panel_name}"


def parse_device_topology(notes: Optional[str]) -> DeviceTopology:
    """
    Parses a notes string into structured DeviceTopology.
    Supported formats:
    - kodetoko/namapanel/fasa (e.g. T105/MDP/R, T105/CHILLER/S, T105/OVEN/1F)
    - kodetoko/namapanel      (e.g. T105/SHOWCASE) -> treated as 1F
    - Freeform text           (e.g. "Gudang Belakang") -> legacy/custom notes
    """
    if not notes:
        return DeviceTopology()

    clean = notes.strip()
    parts = [p.strip() for p in clean.split("/") if p.strip()]

    # Format with 3 or more segments: store / panel / phase
    if len(parts) >= 3:
        store = parts[0].upper()
        panel = parts[1].upper()
        p_raw = parts[2].upper()

        if p_raw in ("R", "S", "T"):
            return DeviceTopology(
                raw=clean,
                store_code=store,
                panel_name=panel,
                phase=p_raw,
                is_valid=True,
                is_three_phase=True
            )
        elif p_raw in ("1F", "1-F", "1", "SINGLE"):
            return DeviceTopology(
                raw=clean,
                store_code=store,
                panel_name=panel,
                phase="1F",
                is_valid=True,
                is_three_phase=False
            )
        else:
            # 3 parts with custom suffix, treat as store / panel / extra
            return DeviceTopology(
                raw=clean,
                store_code=store,
                panel_name=f"{panel} {p_raw}",
                phase=None,
                is_valid=True,
                is_three_phase=False
            )

    # Format with 2 segments: store / panel_or_load
    elif len(parts) == 2:
        store = parts[0].upper()
        panel = parts[1].upper()
        return DeviceTopology(
            raw=clean,
            store_code=store,
            panel_name=panel,
            phase="1F",
            is_valid=True,
            is_three_phase=False
        )

    # Single segment or freeform text
    return DeviceTopology(
        raw=clean,
        store_code="",
        panel_name=clean,
        phase=None,
        is_valid=False,
        is_three_phase=False
    )


def format_device_topology(store_code: str, panel_name: str, phase: Optional[str] = None) -> str:
    """Formats parts into standard kodetoko/namapanel/fasa string."""
    s = store_code.strip().upper()
    p = panel_name.strip().upper()
    ph = phase.strip().upper() if phase else ""

    if s and p and ph:
        return f"{s}/{p}/{ph}"
    elif s and p:
        return f"{s}/{p}"
    elif p and ph:
        return f"{p}/{ph}"
    elif p:
        return p
    return s


def get_topology_sort_key(dev: Any) -> tuple:
    """
    Returns a sort key tuple to group devices by:
    1. Has valid topology (grouped together first)
    2. Store Code (A-Z)
    3. Panel / Load Name (A-Z)
    4. Phase order (R=1, S=2, T=3, 1F=4, Other=5)
    5. Fallback to Device Name
    """
    topo = parse_device_topology(getattr(dev, "notes", None))
    phase_order_map = {"R": 1, "S": 2, "T": 3, "1F": 4}

    if topo.is_valid and topo.store_code:
        # Grouped by store -> panel -> phase
        p_idx = phase_order_map.get(topo.phase, 5) if topo.phase else 5
        return (0, topo.store_code, topo.panel_name, p_idx, getattr(dev, "device_name", ""))
    elif topo.panel_name:
        # Has name but no store code
        return (1, "", topo.panel_name, 9, getattr(dev, "device_name", ""))
    else:
        # No notes / unassigned
        return (2, "ZZZ", "ZZZ", 9, getattr(dev, "device_name", ""))
