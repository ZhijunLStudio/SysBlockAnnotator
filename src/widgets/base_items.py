# src/widgets/base_items.py
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget, QStyle
from PyQt6.QtGui import QPen, QColor, QPainter, QBrush
from PyQt6.QtCore import Qt
from typing import Optional

class SelectableGraphicsItem:
    """A base class for items that can be selected and show a highlight."""
    def paint_selection_highlight(self, painter: QPainter, option: QStyleOptionGraphicsItem):
        if option.state & QStyle.StateFlag.State_Selected:
            # A very obvious highlight: a thick, bright cyan outline
            highlight_pen = QPen(QColor(38, 220, 255), 3, Qt.PenStyle.SolidLine)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(highlight_pen)
            
            # Draw highlight around the item's shape
            if isinstance(self, QGraphicsRectItem):
                painter.drawRect(self.rect())
            elif isinstance(self, QGraphicsPathItem):
                painter.drawPath(self.shape())


class ComponentRectItem(QGraphicsRectItem, SelectableGraphicsItem):
    """A selectable rectangle for components."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable)
        self.setPen(QPen(QColor("#e5c07b"), 2))
        self.setBrush(QColor(229, 192, 123, 30))
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        # First, draw the item itself
        super().paint(painter, option, widget)
        # Then, draw the highlight on top if selected
        self.paint_selection_highlight(painter, option)