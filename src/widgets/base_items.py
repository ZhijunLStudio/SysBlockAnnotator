# src/widgets/base_items.py
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget, QStyle
from PyQt6.QtGui import QPen, QColor, QPainter, QBrush
from PyQt6.QtCore import Qt
from typing import Optional

class SelectableGraphicsItem:
    """A base class for items that can be selected and show a highlight."""
    def paint_selection_highlight(self, painter: QPainter, option: QStyleOptionGraphicsItem):
        if option.state & QStyle.StateFlag.State_Selected:
            # Create the highlight pen
            highlight_pen = QPen(QColor(38, 220, 255), 5, Qt.PenStyle.SolidLine)
            
            # --- MODIFICATION: Make the pen cosmetic ---
            # This makes its width independent of the view's transformation (zoom).
            highlight_pen.setCosmetic(True)

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(highlight_pen)
            
            if isinstance(self, QGraphicsRectItem):
                painter.drawRect(self.rect())
            elif isinstance(self, QGraphicsPathItem):
                painter.drawPath(self.shape())


class ComponentRectItem(QGraphicsRectItem, SelectableGraphicsItem):
    """A selectable rectangle for components."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable)
        
        # Make the component's own border cosmetic as well
        pen = QPen(QColor("#e5c07b"), 2)
        pen.setCosmetic(True)
        self.setPen(pen)

        self.setBrush(QColor(229, 192, 123, 30))
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        super().paint(painter, option, widget)
        self.paint_selection_highlight(painter, option)