"""
Custom QGraphicsItem subclasses for the DXF canvas.

ClickableLineItem wraps a BendLine model object and:
  - Uses QPainterPathStroker to create a wide invisible hit area so thin lines
    are easy to click even at high zoom levels.
  - Left-click cycles the BendState (UNASSIGNED → OUTLINE → POSITIVE → NEGATIVE → …)
  - Right-click / double-click signals a request to edit the bend angle.
  - Hover thickens the pen briefly for visual feedback.
"""

from PySide6.QtWidgets import QGraphicsLineItem
from PySide6.QtGui import QPen, QPainterPath, QPainterPathStroker, QColor
from PySide6.QtCore import Qt, QObject, Signal, QRectF

from .models import BendLine, BendState, BEND_STATE_COLORS, BEND_STATE_CYCLE

# Pixels of click tolerance on each side of the visual line
HIT_HALF_WIDTH: float = 8.0

# Visual pen width for normal state
PEN_WIDTH_NORMAL: float = 1.2
# Visual pen width when hovered
PEN_WIDTH_HOVER: float = 3.0


class LineSignalEmitter(QObject):
    """
    Qt signal proxy for ClickableLineItem.

    QGraphicsLineItem is not a QObject, so it cannot have signals directly.
    A single shared emitter instance is passed to all items.
    """
    left_clicked = Signal(object)   # payload: ClickableLineItem
    right_clicked = Signal(object)  # payload: ClickableLineItem


class ClickableLineItem(QGraphicsLineItem):
    """
    A line segment on the DXF canvas that responds to mouse interaction.

    Parameters
    ----------
    bend_line : BendLine
        The domain model object whose state this item reflects.
    emitter : LineSignalEmitter
        Shared signal proxy used to notify the main window.
    """

    def __init__(self, bend_line: BendLine, emitter: LineSignalEmitter) -> None:
        super().__init__(bend_line.x1, bend_line.y1, bend_line.x2, bend_line.y2)
        self.bend_line = bend_line
        self._emitter = emitter
        self._hovered = False

        self.setAcceptHoverEvents(True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)
        self.setZValue(0)

        self._apply_visual()

    # ------------------------------------------------------------------
    # Hit detection — overridden to give a wide invisible click area
    # ------------------------------------------------------------------

    def shape(self) -> QPainterPath:
        """Return a thick stroke path for hit testing."""
        path = QPainterPath()
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(HIT_HALF_WIDTH * 2)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        return stroker.createStroke(path)

    def boundingRect(self) -> QRectF:
        return self.shape().boundingRect()

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._cycle_state()
            self._emitter.left_clicked.emit(self)
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._emitter.right_clicked.emit(self)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        # Double-click also opens the angle editor
        self._emitter.right_clicked.emit(self)
        event.accept()

    # ------------------------------------------------------------------
    # Hover events — visual feedback only
    # ------------------------------------------------------------------

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        pen = self.pen()
        pen.setWidthF(PEN_WIDTH_HOVER)
        self.setPen(pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self._apply_visual()
        super().hoverLeaveEvent(event)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _cycle_state(self) -> None:
        """Advance the BendState to the next value in the cycle."""
        current_idx = BEND_STATE_CYCLE.index(self.bend_line.state)
        next_idx = (current_idx + 1) % len(BEND_STATE_CYCLE)
        self.bend_line.state = BEND_STATE_CYCLE[next_idx]
        self._apply_visual()

    def refresh_visual(self) -> None:
        """Call this externally when the model state has been changed."""
        self._apply_visual()

    def _apply_visual(self) -> None:
        """Update the pen colour to match the current BendState."""
        color = QColor(BEND_STATE_COLORS[self.bend_line.state])
        pen = QPen(color, PEN_WIDTH_NORMAL)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
