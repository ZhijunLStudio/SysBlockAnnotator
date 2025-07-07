# src/image_viewer.py
import math
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QLineF
from PyQt6.QtGui import QPixmap, QPen, QColor, QPainter
from src.widgets.base_items import ComponentRectItem
from src.drawing_items import ArrowItem

class ImageViewer(QGraphicsView):
    box_drawn = pyqtSignal(QRectF)
    component_clicked = pyqtSignal(str)
    selection_deleted = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.image_item = None
        self.current_mode = 'idle'
        self.start_pos = None
        self.temp_rect = None
        self.component_rects = {}

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(self.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(self.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(self.DragMode.ScrollHandDrag)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
    def set_mode(self, mode, force=False):
        self.current_mode = mode
        if 'drawing_box' in mode:
            self.setDragMode(self.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        elif 'connect' in mode:
            self.setDragMode(self.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else: # idle
            self.setDragMode(self.DragMode.ScrollHandDrag)
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def set_image(self, image_path):
        self.scene.clear()
        self.component_rects.clear()
        
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.image_item = None
            return
            
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)

    def update_annotations(self, data_model, show_all_connections, selected_component_name):
        # Clear old annotations (rects and arrows)
        for item in self.scene.items():
            if item != self.image_item:
                self.scene.removeItem(item)
        self.component_rects.clear()

        # Draw component rects
        if not data_model: return
        for name, details in data_model.components.items():
            box = details['component_box']
            rect = QRectF(box[0], box[1], box[2] - box[0], box[3] - box[1])
            rect_item = ComponentRectItem(rect)
            rect_item.setData(0, name) # Store name in item data
            self.scene.addItem(rect_item)
            self.component_rects[name] = rect_item
        
        # Draw connections
        self._render_connections(data_model, show_all_connections, selected_component_name)

    def _render_connections(self, data_model, show_all, selected_name):
        color_output = QColor("#e06c75")
        color_input = QColor("#98c379")
        color_inout = QColor("#61afef")
        
        drawn_pairs = set()

        for source_name, details in data_model.components.items():
            connections = details.get('connections', {})
            
            # Unidirectional (output -> input)
            for conn in connections.get('output', []):
                target_name = conn.get('name')
                pair = tuple(sorted((source_name, target_name)))
                if pair not in drawn_pairs:
                    self._draw_arrow_if_visible(data_model, source_name, target_name, 'output', conn, show_all, selected_name, color_output, color_input, color_inout)
                    drawn_pairs.add(pair)

            # Bidirectional (inout <-> inout)
            for conn in connections.get('inout', []):
                target_name = conn.get('name')
                pair = tuple(sorted((source_name, target_name)))
                if pair not in drawn_pairs:
                    self._draw_arrow_if_visible(data_model, source_name, target_name, 'inout', conn, show_all, selected_name, color_output, color_input, color_inout)
                    drawn_pairs.add(pair)

    def _draw_arrow_if_visible(self, data_model, source, target, conn_type, conn_details, show_all, selected_name, c_out, c_in, c_inout):
        if source not in self.component_rects or target not in self.component_rects: return

        start_item, end_item = self.component_rects[source], self.component_rects[target]
        to_draw = False
        color = QColor()
        is_bidirectional = (conn_type == 'inout')
        
        if show_all:
            to_draw = True
            color = c_inout if is_bidirectional else c_out
        elif selected_name and (source == selected_name or target == selected_name):
            to_draw = True
            if is_bidirectional:
                color = c_inout
            else: # Unidirectional
                # If we selected the source, it's an output (red)
                # If we selected the target, it's an input (green)
                color = c_out if source == selected_name else c_in
        
        if to_draw:
            count = conn_details.get('count', 1)
            line_vec = end_item.sceneBoundingRect().center() - start_item.sceneBoundingRect().center()
            if line_vec.isNull(): return
            
            # Calculate perpendicular vector for offset
            perp_vec = QPointF(line_vec.y(), -line_vec.x())
            norm_perp = perp_vec / math.sqrt(QPointF.dotProduct(perp_vec, perp_vec)) if not perp_vec.isNull() else QPointF()
            
            spacing = 15.0 # Pixel spacing between parallel lines

            for i in range(count):
                # Offset lines from the center
                offset_val = (i - (count - 1) / 2.0) * spacing
                offset_vec = norm_perp * offset_val
                
                # Create arrow with offset
                arrow = ArrowItem(start_item, end_item, color, source, target, is_bidirectional, offset=offset_vec)
                self.scene.addItem(arrow)

    def highlight_component_rect(self, name, select=True):
        if name in self.component_rects:
            self.component_rects[name].setSelected(select)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = self.scene.selectedItems()
            if selected: self.selection_deleted.emit(selected)
        else: super().keyPressEvent(event)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        component_name_at_pos = self.get_component_name_at(scene_pos)
        
        if 'drawing_box' in self.current_mode and event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = scene_pos
            rect_item = ComponentRectItem(QRectF(self.start_pos, self.start_pos))
            rect_item.setPen(QPen(Qt.GlobalColor.cyan, 2, Qt.PenStyle.DashLine))
            self.temp_rect = rect_item
            self.scene.addItem(self.temp_rect)
        elif 'connect' in self.current_mode or 'idle' in self.current_mode:
             self.component_clicked.emit(component_name_at_pos)
        else:
            super().mousePressEvent(event)

    def get_component_name_at(self, scene_pos):
        items = self.scene.items(scene_pos)
        for item in items:
            if isinstance(item, ComponentRectItem) and item.data(0):
                return item.data(0)
        return None

    def mouseMoveEvent(self, event):
        if 'drawing_box' in self.current_mode and self.start_pos and self.temp_rect:
            pos = self.mapToScene(event.pos())
            self.temp_rect.setRect(QRectF(self.start_pos, pos).normalized())
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if 'drawing_box' in self.current_mode and self.start_pos and self.temp_rect:
            rect = self.temp_rect.rect()
            if self.temp_rect.scene(): self.scene.removeItem(self.temp_rect)
            if rect.width() > 5 and rect.height() > 5:
                self.box_drawn.emit(rect)
            self.temp_rect, self.start_pos = None, None
        else: super().mouseReleaseEvent(event)
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image_item:
            self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)