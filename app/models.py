"""
Core domain model for the Salvagnini P4 DXF GUI application.
All data lives here; Qt and ezdxf are not imported.
"""

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class BendState(Enum):
    """State of a line segment, determining its role in the P4 program."""
    UNASSIGNED = auto()  # Not yet classified (shown in grey)
    OUTLINE = auto()     # Sheet edge / flange outline (shown in black, no BEN: output)
    POSITIVE = auto()    # Positive bend (shown in blue)  → BEN:  L x A y
    NEGATIVE = auto()    # Negative bend (shown in red)   → BEN-: L x A y


# Hex colour for each state when rendered on the canvas
BEND_STATE_COLORS: dict[BendState, str] = {
    BendState.UNASSIGNED: "#888888",  # grey
    BendState.OUTLINE:    "#000000",  # black
    BendState.POSITIVE:   "#0055FF",  # blue
    BendState.NEGATIVE:   "#DD0000",  # red
}

# Left-click cycles through states in this order
BEND_STATE_CYCLE: list[BendState] = [
    BendState.UNASSIGNED,
    BendState.OUTLINE,
    BendState.POSITIVE,
    BendState.NEGATIVE,
]


@dataclass
class BendLine:
    """
    A single straight line segment loaded from a DXF file.

    Arcs are tessellated into multiple BendLine segments by the loader.
    Coordinates are raw DXF world coordinates (no Y-flip applied).
    """
    x1: float
    y1: float
    x2: float
    y2: float
    layer: str = "0"
    state: BendState = BendState.UNASSIGNED
    angle: float = 90.0          # bend angle in degrees (default 90°)
    rot_side: Optional[int] = None   # ROT: side number, set during ordering

    @property
    def length(self) -> float:
        """Euclidean length in DXF units (typically mm)."""
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    @property
    def direction_deg(self) -> float:
        """
        Angle of the line relative to the X axis, in degrees [0, 180).
        Used for geometric grouping into ROT sides.
        """
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        angle = math.degrees(math.atan2(abs(dy), abs(dx)))
        return angle


@dataclass
class PartDimensions:
    """
    Stores the values that appear on the DIM: and REF: lines of the P4 program.
    The user enters these manually before exporting.
    """
    length: float = 0.0       # DIM: X <length>
    width: float = 0.0        # DIM: Z <width>
    thickness: float = 0.0    # DIM: S <thickness>
    ref_x1: float = 0.0       # REF: X1 <ref_x1>
    ref_z1: float = 0.0       # REF: Z1 <ref_z1>
    filename: str = ""        # COD: '<filename>'
