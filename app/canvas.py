"""
Canvas components: DXFScene and DXFView.

DXFScene holds all ClickableLineItem objects.
DXFView provides zoom (mouse wheel) and pan (Space+drag or middle-button).

Y-axis correction:
  DXF uses a right-handed coordinate system where Y increases upward.
  Qt's QGraphicsView uses Y increasing downward.
  We apply QTransform().scale(1.0, -1.0) to the view so that all
  DXF coordinates can be used verbatim without manual negation.
"""

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtGui import QWheelEvent, QTransform, QPainter
from PySide6.QtCore import Qt, QRectF

from .models import BendLine
from .items import ClickableLineItem, LineSignalEmitter

ZOOM_FACTOR: float = 1.15
SCENE_PADDING_FRACTION: float = 0.05  # 5% padding around geometry


class DXFScene(QGraphicsScene):
    """
    Manages all ClickableLineItem objects for the loaded DXF geometry.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setBackgroundBrush(Qt.GlobalColor.white)
        self._line_items: list[ClickableLineItem] = []

    def load_lines(
        self,
        bend_lines: list[BendLine],
        emitter: LineSignalEmitter,
    ) -> None:
        """
        Clear the scene and populate it with items for each BendLine.
        """
        self.clear()
        self._line_items.clear()

        for bl in bend_lines:
            item = ClickableLineItem(bl, emitter)
            self.addItem(item)
            self._line_items.append(item)

        # Compute bounding rect and add padding
        if self._line_items:
            r: QRectF = self.itemsBoundingRect()
            pad = max(r.width(), r.height()) * SCENE_PADDING_FRACTION
            self.setSceneRect(r.adjusted(-pad, -pad, pad, pad))

    def all_items(self) -> list[ClickableLineItem]:
        """Return all line items currently in the scene."""
        return list(self._line_items)

    def refresh_all(self) -> None:
        """Refresh the visual appearance of every item (after bulk state change)."""
        for item in self._line_items:
            item.refresh_visual()


class DXFView(QGraphicsView):
    """
    Interactive graphics view with:
      - Scroll-wheel zoom anchored at cursor position
      - Space-bar hold for pan (ScrollHandDrag)
      - Middle-mouse-button drag for pan
      - Antialiased rendering
      - Y-axis flip to match DXF coordinate system
    """

    def __init__(self, scene: DXFScene) -> None:
        super().__init__(scene)
        self._space_pressed = False

        # Y-flip: DXF Y is up, Qt Y is down
        self.setTransform(QTransform().scale(1.0, -1.0))

        # Zoom anchors at cursor position
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )

        # Default mode: NoDrag so item click events are processed
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        # Visual quality
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        # Allow wheel events to reach the view even when the scene is focussed
        self.setInteractive(True)

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        factor = ZOOM_FACTOR if delta > 0 else 1.0 / ZOOM_FACTOR
        self.scale(factor, factor)
        event.accept()

    # ------------------------------------------------------------------
    # Pan — Space bar hold or middle mouse button
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = True
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        elif event.key() == Qt.Key.Key_F:
            self.fit_all()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = False
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            # Simulate left-button press so ScrollHandDrag activates
            from PySide6.QtGui import QMouseEvent
            fake = QMouseEvent(
                event.type(),
                event.position(),
                event.globalPosition(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                event.modifiers(),
            )
            super().mousePressEvent(fake)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Fit all content in view
    # ------------------------------------------------------------------

    def fit_all(self) -> None:
        """Reset zoom and pan so all geometry is visible."""
        self.fitInView(
            self.scene().sceneRect(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
