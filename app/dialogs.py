"""
Modal dialogs for the Salvagnini P4 application.

AngleDialog        — Edit the bend angle for a single selected line.
PartDimensionsDialog — Enter DIM: / REF: values before export.
"""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QGroupBox,
    QVBoxLayout,
)
from PySide6.QtCore import Qt

from .models import PartDimensions


class AngleDialog(QDialog):
    """
    Small dialog opened when the user right-clicks / double-clicks a bend line.
    Shows the line length for reference and lets the user change the bend angle.
    """

    def __init__(
        self,
        current_angle: float,
        line_length: float,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Bend Angle")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.setMinimumWidth(300)

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Read-only line length
        length_label = QLabel(f"{line_length:.3f} mm")
        layout.addRow("Line length:", length_label)

        # Angle spinbox
        self._spin = QDoubleSpinBox()
        self._spin.setRange(0.1, 180.0)
        self._spin.setSingleStep(0.5)
        self._spin.setDecimals(1)
        self._spin.setValue(current_angle)
        self._spin.setSuffix("°")
        layout.addRow("Bend angle:", self._spin)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_angle(self) -> float:
        """Return the angle value entered by the user."""
        return self._spin.value()


class PartDimensionsDialog(QDialog):
    """
    Dialog for entering DIM: and REF: values, and the program name (COD:).
    Opens automatically before the user saves a P4 program file.
    """

    def __init__(self, dims: PartDimensions, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Part Dimensions / P4 Program Header")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.setMinimumWidth(380)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # --- COD: group ---
        cod_group = QGroupBox("Program Name (COD:)")
        cod_form = QFormLayout(cod_group)
        self._filename_edit = QLineEdit(dims.filename or "")
        self._filename_edit.setPlaceholderText("e.g.  Test_Vyrobok")
        cod_form.addRow("Program name:", self._filename_edit)
        main_layout.addWidget(cod_group)

        # --- DIM: group ---
        dim_group = QGroupBox("Blank Dimensions (DIM:)")
        dim_form = QFormLayout(dim_group)

        self._length_spin = _make_spin(dims.length, "mm")
        self._width_spin = _make_spin(dims.width, "mm")
        self._thickness_spin = _make_spin(dims.thickness, "mm", max_val=20.0)

        dim_form.addRow("Length X:", self._length_spin)
        dim_form.addRow("Width Z:", self._width_spin)
        dim_form.addRow("Thickness S:", self._thickness_spin)
        main_layout.addWidget(dim_group)

        # --- REF: group ---
        ref_group = QGroupBox("Reference Point (REF:)")
        ref_form = QFormLayout(ref_group)

        self._ref_x1_spin = _make_spin(dims.ref_x1, "mm")
        self._ref_z1_spin = _make_spin(dims.ref_z1, "mm")

        ref_form.addRow("REF X1:", self._ref_x1_spin)
        ref_form.addRow("REF Z1:", self._ref_z1_spin)
        main_layout.addWidget(ref_group)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def get_dims(self) -> PartDimensions:
        """Return a PartDimensions object reflecting the current dialog values."""
        return PartDimensions(
            length=self._length_spin.value(),
            width=self._width_spin.value(),
            thickness=self._thickness_spin.value(),
            ref_x1=self._ref_x1_spin.value(),
            ref_z1=self._ref_z1_spin.value(),
            filename=self._filename_edit.text().strip() or "Part",
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_spin(
    value: float,
    suffix: str = "",
    max_val: float = 9999.0,
) -> QDoubleSpinBox:
    """Create a standard double spinbox for dimension entry."""
    spin = QDoubleSpinBox()
    spin.setRange(0.0, max_val)
    spin.setDecimals(3)
    spin.setSingleStep(0.5)
    spin.setValue(value)
    if suffix:
        spin.setSuffix(f" {suffix}")
    return spin
