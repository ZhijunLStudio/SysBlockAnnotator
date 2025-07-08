# src/drawing_items.py
import math
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget
from PyQt6.QtGui import QPainterPath, QPen, QColor, QPolygonF, QBrush, QPainter, QPainterPathStroker
from PyQt6.QtCore import QPointF, Qt, QRectF, QLineF
from typing import Optional
from src.widgets.base_items import SelectableGraphicsItem, QGraphicsPathItem

class ArrowItem(QGraphicsPathItem, SelectableGraphicsItem):
    def __init__(self, start_item, end_item, color: QColor, source_name, target_name, 
                 is_bidirectional: bool, offset: QPointF = QPointF(0, 0), 
                 line_width: int = 3, parent=None):
        super().__init__(parent)
        self.start_item = start_item
        self.end_item = end_item
        self.arrow_color = color
        self.source_name = source_name
        self.target_name = target_name
        self.is_bidirectional = is_bidirectional
        self.conn_type = 'inout' if is_bidirectional else 'output'
        self.offset = offset
        self.line_width = line_width

        self.line_start, self.line_end = QPointF(), QPointF()
        
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable)
        self.update_path()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create a cosmetic pen for the line
        line_pen = QPen(self.arrow_color, self.line_width, Qt.PenStyle.SolidLine)
        line_pen.setCosmetic(True)
        painter.setPen(line_pen)
        painter.drawLine(self.line_start, self.line_end)
        
        # --- DYNAMIC ARROWHEAD CALCULATION ---
        # The arrowhead size should also be constant on screen, so we calculate it
        # based on the current level of detail (zoom factor).
        lod = painter.worldTransform().m11() # Get the current zoom level
        if lod == 0: return # Avoid division by zero
        
        # Define arrowhead size in screen pixels
        arrow_size_on_screen = 15.0
        # Calculate the required size in scene coordinates
        arrow_size_in_scene = arrow_size_on_screen / lod

        line_vec = self.line_end - self.line_start
        if line_vec.isNull(): return

        # Calculate arrowhead for the end point
        angle_end = math.atan2(line_vec.y(), line_vec.x())
        p1 = self.line_end - QPointF(math.cos(angle_end - math.pi / 6) * arrow_size_in_scene, math.sin(angle_end - math.pi / 6) * arrow_size_in_scene)
        p2 = self.line_end - QPointF(math.cos(angle_end + math.pi / 6) * arrow_size_in_scene, math.sin(angle_end + math.pi / 6) * arrow_size_in_scene)
        arrow_head_end = QPolygonF([self.line_end, p1, p2])

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.arrow_color))
        painter.drawPolygon(arrow_head_end)

        # Calculate and draw arrowhead for the start point if bidirectional
        if self.is_bidirectional:
            angle_start = math.atan2(-line_vec.y(), -line_vec.x())
            p3 = self.line_start - QPointF(math.cos(angle_start - math.pi / 6) * arrow_size_in_scene, math.sin(angle_start - math.pi / 6) * arrow_size_in_scene)
            p4 = self.line_start - QPointF(math.cos(angle_start + math.pi / 6) * arrow_size_in_scene, math.sin(angle_start + math.pi / 6) * arrow_size_in_scene)
            arrow_head_start = QPolygonF([self.line_start, p3, p4])
            painter.drawPolygon(arrow_head_start)
        
        # This still uses the cosmetic pen set in the base class, which is correct
        self.paint_selection_highlight(painter, option)

    def update_path(self):
        """This method now only calculates the start and end points of the line."""
        start_pos = self.start_item.sceneBoundingRect().center() + self.offset
        end_pos = self.end_item.sceneBoundingRect().center() + self.offset
        
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

    def shape(self):
        path = QPainterPath()
        if self.line_start.isNull() or self.line_end.isNull(): return path
        path.moveTo(self.line_start)
        path.lineTo(self.line_end)
        
        # The clickable area of the line should also be cosmetic
        stroker = QPainterPathStroker()
        stroker.setWidth(15)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        # Create a cosmetic stroke
        stroke = stroker.createStroke(path)
        
        # We need to manually scale the shape to be independent of the view's transform
        # This is an advanced technique, but it makes the clickable area consistent.
        # However, for simplicity and robustness, a fixed large width is often sufficient.
        # Let's stick to the simpler approach for now.
        return stroke