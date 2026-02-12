"""
Salvagnini P4 program file generator (post-processor).

Produces plain-text output following the syntax documented in the
Salvagnini P4 programming manual.  Numbers always use a decimal point,
never a comma (e.g. 90.0, not 90,0).

Example output
--------------
COD: 'Test_Vyrobok'
DIM: X 1000.000 Z 500.000 S 1.500
REF: X1 500.000 Z1 250.000
ROT: S 1
BEN:  L 100.000 A 90.0
BEN-: L 50.000 A 135.0
ROT: S 2
BEN:  L 200.000 A 90.0
END:
"""

import os
from .models import BendLine, BendState, PartDimensions


def generate_p4_text(
    dims: PartDimensions,
    rot_sides: list[list[BendLine]],
) -> str:
    """
    Build and return the complete P4 program text as a string.

    Parameters
    ----------
    dims : PartDimensions
        Header values (filename, blank dimensions, reference point).
    rot_sides : list[list[BendLine]]
        Ordered list of ROT sides; each sub-list contains the BendLines
        that belong to that side (only POSITIVE/NEGATIVE states are output).

    Returns
    -------
    str
        The complete P4 program text, with CRLF line endings as required
        by some Salvagnini controllers.  ASCII-safe characters only.
    """
    filename = _sanitize_name(dims.filename or "Part")
    out: list[str] = []

    # --- Header ---
    out.append(f"COD: '{filename}'")
    out.append(
        f"DIM: X {dims.length:.3f} Z {dims.width:.3f} S {dims.thickness:.3f}"
    )
    out.append(
        f"REF: X1 {dims.ref_x1:.3f} Z1 {dims.ref_z1:.3f}"
    )

    # --- Bends ---
    if not rot_sides:
        # No bends defined yet — still produce a valid (empty) program
        out.append("ROT: S 1")
    else:
        for side_num, side_lines in enumerate(rot_sides, start=1):
            out.append(f"ROT: S {side_num}")
            for bl in side_lines:
                if bl.state == BendState.POSITIVE:
                    out.append(f"BEN:  L {bl.length:.3f} A {bl.angle:.1f}")
                elif bl.state == BendState.NEGATIVE:
                    out.append(f"BEN-: L {bl.length:.3f} A {bl.angle:.1f}")
                # OUTLINE / UNASSIGNED → no BEN line

    # --- Footer ---
    out.append("END:")

    return "\n".join(out)


def write_p4_file(
    filepath: str,
    dims: PartDimensions,
    rot_sides: list[list[BendLine]],
) -> str:
    """
    Generate the P4 program text and write it to *filepath*.

    Returns the generated text so callers can display it in the preview pane.
    The file is written as ASCII text with LF line endings.
    """
    text = generate_p4_text(dims, rot_sides)
    with open(filepath, "w", encoding="ascii", errors="replace", newline="\n") as fh:
        fh.write(text)
    return text


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sanitize_name(name: str) -> str:
    """
    Strip or replace characters that are not allowed in a Salvagnini program name.
    Spaces are replaced with underscores; the extension is removed.
    """
    base = os.path.splitext(os.path.basename(name))[0]
    # Replace whitespace and characters unsafe in single-quoted P4 identifiers
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in base)
    return safe or "Part"
