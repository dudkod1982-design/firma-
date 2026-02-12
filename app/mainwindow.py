"""
Main application window.

Wires together DXFScene/DXFView, the ClickableLineItem signals,
the angle/dimensions dialogs, the ROT-side ordering list, and the
P4 output writer.

Layout
------
┌──────────────────────────────────────────────┬──────────────────┐
│                                              │  Right panel:    │
│         DXFView  (canvas)                   │  - File buttons  │
│                                              │  - Legend        │
│                                              │  - Layer filter  │
│                                              │  - Bend order    │
│                                              │  - P4 preview    │
└──────────────────────────────────────────────┴──────────────────┘
│  Status bar                                                       │
└───────────────────────────────────────────────────────────────────┘
"""

import os

from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtCore import Qt

from .canvas import DXFScene, DXFView
from .dialogs import AngleDialog, PartDimensionsDialog
from .dxf_loader import load_dxf
from .items import LineSignalEmitter, ClickableLineItem
from .models import BendLine, BendState, PartDimensions
from .output_writer import generate_p4_text, write_p4_file
from .rot_ordering import auto_order_sides, sides_to_flat_list

# Width of the right-hand control panel in pixels
RIGHT_PANEL_WIDTH = 300


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Firma — Salvagnini P4 Programmer")
        self.resize(1400, 850)

        # Application state
        self._bend_lines: list[BendLine] = []
        self._dims = PartDimensions()
        self._rot_sides: list[list[BendLine]] = []
        self._current_dxf_path: str = ""

        # Signal proxy shared by all line items
        self._emitter = LineSignalEmitter()
        self._emitter.left_clicked.connect(self._on_line_left_clicked)
        self._emitter.right_clicked.connect(self._on_line_right_clicked)

        self._build_ui()
        self._build_shortcuts()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # --- Canvas ---
        self._scene = DXFScene()
        self._view = DXFView(self._scene)
        self._view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        splitter.addWidget(self._view)

        # --- Right panel ---
        right_widget = QWidget()
        right_widget.setFixedWidth(RIGHT_PANEL_WIDTH)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(8)

        right_layout.addWidget(self._build_file_group())
        right_layout.addWidget(self._build_legend_group())
        right_layout.addWidget(self._build_layers_group())
        right_layout.addWidget(self._build_order_group())
        right_layout.addWidget(self._build_preview_group(), stretch=1)

        splitter.addWidget(right_widget)
        splitter.setSizes([1100, RIGHT_PANEL_WIDTH])

        # --- Status bar ---
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready — open a DXF file to begin.")

    def _build_file_group(self) -> QGroupBox:
        group = QGroupBox("File")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        self._btn_open = QPushButton("Open DXF…  (Ctrl+O)")
        self._btn_fit = QPushButton("Fit View  (F)")
        self._btn_export = QPushButton("Export P4 Program…  (Ctrl+S)")
        self._btn_export.setEnabled(False)

        for btn in (self._btn_open, self._btn_fit, self._btn_export):
            layout.addWidget(btn)

        self._btn_open.clicked.connect(self._open_dxf)
        self._btn_fit.clicked.connect(self._view.fit_all)
        self._btn_export.clicked.connect(self._export)

        return group

    def _build_legend_group(self) -> QGroupBox:
        group = QGroupBox("Legend  (click to cycle state)")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        entries = [
            ("#888888", "Unassigned (grey)"),
            ("#000000", "Outline edge — no BEN output"),
            ("#0055FF", "Positive bend → BEN:"),
            ("#DD0000", "Negative bend → BEN-:"),
        ]
        for color_hex, text in entries:
            lbl = QLabel(f"  ■  {text}")
            lbl.setStyleSheet(
                f"color: {color_hex}; font-weight: bold; font-size: 11px;"
            )
            layout.addWidget(lbl)

        return group

    def _build_layers_group(self) -> QGroupBox:
        group = QGroupBox("Layers (show/hide)")
        layout = QVBoxLayout(group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(120)
        inner = QWidget()
        self._layers_layout = QVBoxLayout(inner)
        self._layers_layout.setContentsMargins(4, 4, 4, 4)
        self._layers_layout.setSpacing(2)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        return group

    def _build_order_group(self) -> QGroupBox:
        group = QGroupBox("Bend Order — ROT: sides")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        self._order_list = QListWidget()
        self._order_list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self._order_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._order_list.setMaximumHeight(140)
        self._order_list.setToolTip(
            "Drag rows to change the bend sequence.\n"
            "Each ROT: S block is separated by a blank row."
        )
        layout.addWidget(self._order_list)

        btn_auto = QPushButton("Auto-order bends")
        btn_auto.setToolTip(
            "Group bend lines by geometric direction\n"
            "(horizontal / vertical) and sort spatially."
        )
        btn_auto.clicked.connect(self._auto_order)
        layout.addWidget(btn_auto)

        return group

    def _build_preview_group(self) -> QGroupBox:
        group = QGroupBox("P4 Output Preview")
        layout = QVBoxLayout(group)

        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(
            self._preview.font().__class__(
                "Courier New", 9
            )
        )
        self._preview.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._preview)

        return group

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self, self._open_dxf)
        QShortcut(QKeySequence("Ctrl+S"), self, self._export)
        QShortcut(QKeySequence("F"), self._view, self._view.fit_all)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _open_dxf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open DXF File",
            "",
            "DXF Files (*.dxf *.DXF);;All Files (*)",
        )
        if not path:
            return

        try:
            self._bend_lines = load_dxf(path)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error loading DXF", f"Could not load file:\n{exc}"
            )
            return

        self._current_dxf_path = path
        self._dims.filename = os.path.splitext(os.path.basename(path))[0]
        self._rot_sides = []

        # Populate canvas
        self._scene.load_lines(self._bend_lines, self._emitter)
        self._view.fit_all()

        # Populate layer checkboxes
        self._rebuild_layer_panel()

        # Estimate dimensions from bounding box
        self._estimate_dims_from_bbox()

        # Reset order list
        self._order_list.clear()

        # Update UI
        self._btn_export.setEnabled(True)
        self._update_preview()

        self._status.showMessage(
            f"Loaded {len(self._bend_lines)} segments from: {path}"
        )

    def _estimate_dims_from_bbox(self) -> None:
        """Fill in DIM:/REF: defaults from the bounding box of all lines."""
        if not self._bend_lines:
            return
        xs = [c for bl in self._bend_lines for c in (bl.x1, bl.x2)]
        ys = [c for bl in self._bend_lines for c in (bl.y1, bl.y2)]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max_x - min_x
        h = max_y - min_y
        self._dims.length = round(w, 3)
        self._dims.width = round(h, 3)
        self._dims.ref_x1 = round(w / 2.0, 3)
        self._dims.ref_z1 = round(h / 2.0, 3)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export(self) -> None:
        if not self._bend_lines:
            QMessageBox.information(
                self, "No data", "Please open a DXF file first."
            )
            return

        # Ask for part dimensions
        dlg = PartDimensionsDialog(self._dims, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._dims = dlg.get_dims()

        # File save dialog
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Salvagnini P4 Program",
            self._dims.filename + ".p4",
            "P4 Program Files (*.p4);;Text Files (*.txt);;All Files (*)",
        )
        if not save_path:
            return

        # Build sides if not already ordered
        if not self._rot_sides:
            self._rot_sides = auto_order_sides(self._bend_lines)

        try:
            text = write_p4_file(save_path, self._dims, self._rot_sides)
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Error", f"Could not write file:\n{exc}"
            )
            return

        self._preview.setText(text)
        self._status.showMessage(f"Exported P4 program: {save_path}")

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_line_left_clicked(self, item: ClickableLineItem) -> None:
        """Update status bar and refresh preview after a state change."""
        bl = item.bend_line
        state_name = bl.state.name.replace("_", " ").title()
        self._status.showMessage(
            f"Line — Length: {bl.length:.3f} mm  |  "
            f"State: {state_name}  |  "
            f"Angle: {bl.angle:.1f}°  |  "
            f"Layer: {bl.layer}"
        )
        # Rebuild sides and update preview
        self._rot_sides = auto_order_sides(self._bend_lines)
        self._refresh_order_list()
        self._update_preview()

    def _on_line_right_clicked(self, item: ClickableLineItem) -> None:
        """Open AngleDialog for the clicked line."""
        bl = item.bend_line
        if bl.state not in (BendState.POSITIVE, BendState.NEGATIVE):
            self._status.showMessage(
                "Right-click / double-click: assign the line as a bend first "
                "(left-click twice to set to Positive, three times for Negative)."
            )
            return

        dlg = AngleDialog(bl.angle, bl.length, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            bl.angle = dlg.get_angle()
            self._rot_sides = auto_order_sides(self._bend_lines)
            self._refresh_order_list()
            self._update_preview()
            self._status.showMessage(
                f"Angle updated to {bl.angle:.1f}° — length: {bl.length:.3f} mm"
            )

    # ------------------------------------------------------------------
    # ROT ordering
    # ------------------------------------------------------------------

    def _auto_order(self) -> None:
        """Run auto-ordering heuristic and populate the order list widget."""
        self._rot_sides = auto_order_sides(self._bend_lines)
        self._refresh_order_list()
        self._update_preview()
        count = sum(len(s) for s in self._rot_sides)
        self._status.showMessage(
            f"Auto-ordered {count} bend(s) into {len(self._rot_sides)} ROT side(s)."
        )

    def _refresh_order_list(self) -> None:
        """Repopulate the QListWidget from the current rot_sides list."""
        self._order_list.clear()
        for side_num, side_lines in enumerate(self._rot_sides, start=1):
            for bl in side_lines:
                direction = "↑ BEN:" if bl.state == BendState.POSITIVE else "↓ BEN-:"
                text = (
                    f"ROT {side_num}  {direction}  "
                    f"L={bl.length:.1f}  A={bl.angle:.1f}°"
                )
                item = QListWidgetItem(text)
                color = "#0055FF" if bl.state == BendState.POSITIVE else "#DD0000"
                item.setForeground(QColor(color))
                self._order_list.addItem(item)

    # ------------------------------------------------------------------
    # Layer panel
    # ------------------------------------------------------------------

    def _rebuild_layer_panel(self) -> None:
        """Recreate the layer checkboxes after loading a new DXF."""
        # Remove existing checkboxes
        while self._layers_layout.count():
            child = self._layers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Collect unique layer names
        layers = sorted({bl.layer for bl in self._bend_lines})
        for layer_name in layers:
            cb = QCheckBox(layer_name)
            cb.setChecked(True)
            cb.toggled.connect(
                lambda checked, ln=layer_name: self._toggle_layer(ln, checked)
            )
            self._layers_layout.addWidget(cb)

    def _toggle_layer(self, layer_name: str, visible: bool) -> None:
        """Show or hide all items belonging to the given layer."""
        for item in self._scene.all_items():
            if item.bend_line.layer == layer_name:
                item.setVisible(visible)

    # ------------------------------------------------------------------
    # Live preview
    # ------------------------------------------------------------------

    def _update_preview(self) -> None:
        """Regenerate the P4 output text and show it in the preview pane."""
        if not self._bend_lines:
            self._preview.clear()
            return
        if not self._rot_sides:
            self._rot_sides = auto_order_sides(self._bend_lines)
        text = generate_p4_text(self._dims, self._rot_sides)
        self._preview.setText(text)
