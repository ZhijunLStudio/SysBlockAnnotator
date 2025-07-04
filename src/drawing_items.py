# src/drawing_items.py
import math
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget
from PyQt6.QtGui import QPainterPath, QPen, QColor, QPolygonF, QBrush, QPainter, QPainterPathStroker
from PyQt6.QtCore import QPointF, Qt, QRectF, QLineF
from typing import Optional

# Import the new base class
from src.widgets.base_items import SelectableGraphicsItem, QGraphicsPathItem

class ArrowItem(QGraphicsPathItem, SelectableGraphicsItem):
    """Arrow item with clear selection highlight."""
    def __init__(self, start_item, end_item, color: QColor, source_name, target_name, is_bidirectional: bool, parent=None):
        super().__init__(parent)
        self.start_item = start_item
        self.end_item = end_item
        self.arrow_color = color
        self.source_name = source_name
        self.target_name = target_name
        self.is_bidirectional = is_bidirectional
        self.conn_type = 'inout' if is_bidirectional else 'output'

        self.line_start, self.line_end = QPointF(), QPointF()
        self.arrow_head_end, self.arrow_head_start = QPolygonF(), QPolygonF()
        
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable)
        self.update_path()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        line_pen = QPen(self.arrow_color, 3, Qt.PenStyle.SolidLine)
        painter.setPen(line_pen)
        painter.drawLine(self.line_start, self.line_end)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.arrow_color))
        painter.drawPolygon(self.arrow_head_end)
        if self.is_bidirectional:
            painter.drawPolygon(self.arrow_head_start)
        
        # Use the unified selection painting method from the base class
        self.paint_selection_highlight(painter, option)

    def update_path(self):
        start_pos = self.start_item.sceneBoundingRect().center()
        end_pos = self.end_item.sceneBoundingRect().center()
        
        line = end_pos - start_pos
        if line.isNull(): return

        def get_intersection_point(rect: QRectF, line_vec: QPointF, center: QPointF):
            if rect.isEmpty() or line_vec.isNull(): return center
            p_far = center + line_vec * 1000
            intersect_line = QLineF(center, p_far)
            
            sides = [QLineF(rect.topLeft(), rect.topRight()), QLineF(rect.topRight(), rect.bottomRight()),
                     QLineF(rect.bottomRight(), rect.bottomLeft()), QLineF(rect.bottomLeft(), rect.topLeft())]
            
            for side in sides:
                intersection_type, point = side.intersects(intersect_line)
                if intersection_type == QLineF.IntersectionType.BoundedIntersection:
                    return point
            return center

        self.line_start = get_intersection_point(self.start_item.rect(), line, start_pos)
        self.line_end = get_intersection_point(self.end_item.rect(), -line, end_pos)
        
        line_vec = self.line_end - self.line_start
        if line_vec.isNull(): return

        angle = math.atan2(line_vec.y(), line_vec.x())
        arrow_size = 15.0

        p1 = self.line_end - QPointF(math.cos(angle - math.pi / 6) * arrow_size, math.sin(angle - math.pi / 6) * arrow_size)
        p2 = self.line_end - QPointF(math.cos(angle + math.pi / 6) * arrow_size, math.sin(angle + math.pi / 6) * arrow_size)
        self.arrow_head_end = QPolygonF([self.line_end, p1, p2])

        angle_start = math.atan2(-line_vec.y(), -line_vec.x())
        p3 = self.line_start - QPointF(math.cos(angle_start - math.pi / 6) * arrow_size, -math.sin(angle_start - math.pi / 6) * arrow_size)
        p4 = self.line_start - QPointF(math.cos(angle_start + math.pi / 6) * arrow_size, -math.sin(angle_start + math.pi / 6) * arrow_size)
        self.arrow_head_start = QPolygonF([self.line_start, p3, p4])

    def shape(self):
        path = QPainterPath()
        if self.line_start.isNull() or self.line_end.isNull():
            return path
        path.moveTo(self.line_start)
        path.lineTo(self.line_end)
        stroker = QPainterPathStroker()
        stroker.setWidth(15)  # Make the selection area wider
        return stroker.createStroke(path)