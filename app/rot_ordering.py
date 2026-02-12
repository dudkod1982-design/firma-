"""
ROT: side ordering for the Salvagnini P4 output.

The P4 program groups bends by "side" — a set of bends that the machine
performs before rotating the sheet.  Between sides the controller inserts
a ROT: S <n> command.

This module provides:

  auto_order_sides(bend_lines) → list[list[BendLine]]
      Heuristic grouping: lines that run in the same geometric direction
      (horizontal vs. vertical, snapped to 10° buckets) are placed on the
      same side.  Within each side the lines are sorted spatially so the
      operator can inspect the sequence easily.

The result is always a suggestion — the user can drag-reorder entries in the
QListWidget in the main window before exporting.
"""

import math
from collections import defaultdict

from .models import BendLine, BendState

# Angular bucket width used to cluster bend-line directions
DIRECTION_BUCKET_DEG: float = 15.0


def auto_order_sides(bend_lines: list[BendLine]) -> list[list[BendLine]]:
    """
    Group active bend lines (POSITIVE or NEGATIVE) into ROT sides.

    Algorithm
    ---------
    1. Compute the direction of each line (0–180°).
    2. Snap the direction to DIRECTION_BUCKET_DEG-wide buckets.
    3. Lines in the same bucket go on the same ROT side.
    4. Sides are sorted roughly from bottom-left to top-right
       (same order a human would typically program).
    5. Within each side, lines are sorted spatially.

    Parameters
    ----------
    bend_lines : list[BendLine]
        Full list of BendLine objects (UNASSIGNED and OUTLINE are ignored).

    Returns
    -------
    list[list[BendLine]]
        Each sub-list is the set of bends for one ROT: block, ordered
        spatially within that side.
    """
    active = [
        bl for bl in bend_lines
        if bl.state in (BendState.POSITIVE, BendState.NEGATIVE)
    ]

    if not active:
        return []

    # --- Step 1 & 2: bucket by direction ---
    buckets: dict[int, list[BendLine]] = defaultdict(list)
    for bl in active:
        bucket = _direction_bucket(bl)
        buckets[bucket].append(bl)

    # --- Step 3: sort within each bucket spatially ---
    result: list[list[BendLine]] = []
    for bucket_key in sorted(buckets.keys()):
        group = buckets[bucket_key]
        group = _sort_spatially(group, bucket_key)
        result.append(group)

    return result


def _direction_bucket(bl: BendLine) -> int:
    """
    Return an integer bucket index representing the direction of the line.

    Lines nearly parallel to the X axis get bucket 0.
    Lines at 45° get bucket 3 (45 / 15 = 3).
    Lines nearly parallel to Y axis get bucket 6 (90 / 15 = 6).
    """
    dx = bl.x2 - bl.x1
    dy = bl.y2 - bl.y1
    angle_deg = math.degrees(math.atan2(abs(dy), abs(dx)))  # 0–90
    bucket = round(angle_deg / DIRECTION_BUCKET_DEG)
    return int(bucket)


def _sort_spatially(group: list[BendLine], bucket: int) -> list[BendLine]:
    """
    Sort lines within a group by spatial position.

    Near-horizontal lines (bucket < 3): sort by Y mid-point (bottom first).
    Near-vertical lines (bucket ≥ 3):   sort by X mid-point (left first).
    """
    near_horizontal = bucket < 3

    def sort_key(bl: BendLine):
        mid_x = (bl.x1 + bl.x2) / 2.0
        mid_y = (bl.y1 + bl.y2) / 2.0
        if near_horizontal:
            return (round(mid_y, 1), mid_x)
        else:
            return (round(mid_x, 1), mid_y)

    return sorted(group, key=sort_key)


def sides_to_flat_list(sides: list[list[BendLine]]) -> list[tuple[int, BendLine]]:
    """
    Utility: flatten sides into (side_number, BendLine) pairs.
    Useful for populating a QListWidget.
    """
    result: list[tuple[int, BendLine]] = []
    for i, side in enumerate(sides, start=1):
        for bl in side:
            result.append((i, bl))
    return result
