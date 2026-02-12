"""
DXF file parser.

Reads LINE, ARC, LWPOLYLINE and POLYLINE entities from the model space
of a DXF file and converts them into a flat list of BendLine objects.
Arcs are tessellated into straight segments.
Coincident/duplicate lines are removed.
"""

import math
from typing import Generator

import ezdxf
from ezdxf.recover import readfile as recover_readfile

from .models import BendLine

# Angular step for arc tessellation (degrees per segment)
ARC_STEP_DEG: float = 5.0

# Deduplication tolerance in DXF units (mm)
DEDUP_TOLERANCE: float = 0.01


def load_dxf(filepath: str) -> list[BendLine]:
    """
    Parse a DXF file and return all line segments from model space.

    Uses ezdxf.recover to handle slightly malformed DXF files.
    Returns raw DXF world coordinates — no Y-axis flip is applied here.
    """
    try:
        doc = ezdxf.readfile(filepath)
    except Exception:
        # Fall back to tolerant parser
        doc, _ = recover_readfile(filepath)

    msp = doc.modelspace()
    lines: list[BendLine] = []

    for entity in msp:
        dxftype = entity.dxftype()
        layer = entity.dxf.get("layer", "0")

        if dxftype == "LINE":
            lines.extend(_parse_line(entity, layer))
        elif dxftype == "ARC":
            lines.extend(_parse_arc(entity, layer))
        elif dxftype == "LWPOLYLINE":
            lines.extend(_parse_lwpolyline(entity, layer))
        elif dxftype == "POLYLINE":
            lines.extend(_parse_polyline(entity, layer))
        elif dxftype == "SPLINE":
            lines.extend(_parse_spline(entity, layer))

    return _deduplicate(lines)


# ---------------------------------------------------------------------------
# Entity parsers
# ---------------------------------------------------------------------------

def _parse_line(entity, layer: str) -> list[BendLine]:
    s = entity.dxf.start
    e = entity.dxf.end
    bl = BendLine(float(s.x), float(s.y), float(e.x), float(e.y), layer=layer)
    if bl.length > DEDUP_TOLERANCE:
        return [bl]
    return []


def _parse_arc(entity, layer: str) -> list[BendLine]:
    """Tessellate an ARC entity into straight BendLine segments."""
    cx = float(entity.dxf.center.x)
    cy = float(entity.dxf.center.y)
    r = float(entity.dxf.radius)
    start_ang = float(entity.dxf.start_angle)
    end_ang = float(entity.dxf.end_angle)

    # DXF arcs run counter-clockwise; end < start means they cross 0°
    if end_ang < start_ang:
        end_ang += 360.0

    segments: list[BendLine] = []
    a = start_ang
    while a < end_ang:
        a_next = min(a + ARC_STEP_DEG, end_ang)
        x1 = cx + r * math.cos(math.radians(a))
        y1 = cy + r * math.sin(math.radians(a))
        x2 = cx + r * math.cos(math.radians(a_next))
        y2 = cy + r * math.sin(math.radians(a_next))
        bl = BendLine(x1, y1, x2, y2, layer=layer)
        if bl.length > DEDUP_TOLERANCE:
            segments.append(bl)
        a = a_next

    return segments


def _parse_lwpolyline(entity, layer: str) -> list[BendLine]:
    """Convert LWPOLYLINE vertices into BendLine segments."""
    # get_points returns (x, y, start_width, end_width, bulge) tuples
    points = [(p[0], p[1]) for p in entity.get_points()]
    return _points_to_segments(points, entity.is_closed, layer)


def _parse_polyline(entity, layer: str) -> list[BendLine]:
    """Convert a 2D POLYLINE into BendLine segments."""
    try:
        points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
    except Exception:
        return []
    closed = bool(getattr(entity.dxf, "flags", 0) & 1)
    return _points_to_segments(points, closed, layer)


def _parse_spline(entity, layer: str) -> list[BendLine]:
    """Approximate a SPLINE by sampling its control points as line segments."""
    try:
        # Use the approximation method if available
        points = list(entity.approximate(segments=50))
        pts = [(p[0], p[1]) for p in points]
        return _points_to_segments(pts, False, layer)
    except Exception:
        return []


def _points_to_segments(
    points: list[tuple[float, float]],
    closed: bool,
    layer: str,
) -> list[BendLine]:
    """Convert an ordered list of (x, y) points into BendLine segments."""
    segments: list[BendLine] = []
    n = len(points)
    if n < 2:
        return segments
    for i in range(n - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        bl = BendLine(float(x1), float(y1), float(x2), float(y2), layer=layer)
        if bl.length > DEDUP_TOLERANCE:
            segments.append(bl)
    if closed and n >= 2:
        x1, y1 = points[-1]
        x2, y2 = points[0]
        bl = BendLine(float(x1), float(y1), float(x2), float(y2), layer=layer)
        if bl.length > DEDUP_TOLERANCE:
            segments.append(bl)
    return segments


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _snap(value: float) -> int:
    """Snap a coordinate value to an integer grid for comparison."""
    return round(value / DEDUP_TOLERANCE)


def _deduplicate(lines: list[BendLine]) -> list[BendLine]:
    """
    Remove duplicate line segments (same endpoints within DEDUP_TOLERANCE,
    in either direction).
    """
    seen: set[tuple[int, int, int, int]] = set()
    result: list[BendLine] = []

    for bl in lines:
        k1 = (_snap(bl.x1), _snap(bl.y1), _snap(bl.x2), _snap(bl.y2))
        k2 = (_snap(bl.x2), _snap(bl.y2), _snap(bl.x1), _snap(bl.y1))
        if k1 not in seen and k2 not in seen:
            seen.add(k1)
            result.append(bl)

    return result
