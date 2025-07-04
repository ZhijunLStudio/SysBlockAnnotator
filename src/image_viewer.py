# src/image_viewer.py
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
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
        
    # --- FIX: Added the 'force' keyword argument to match the call from MainWindow ---
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
        for item in self.scene.items():
            if item != self.image_item:
                self.scene.removeItem(item)
        self.component_rects.clear()

        for name, details in data_model.components.items():
            box = details['component_box']
            rect = QRectF(box[0], box[1], box[2] - box[0], box[3] - box[1])
            rect_item = ComponentRectItem(rect)
            rect_item.setData(0, name)
            self.scene.addItem(rect_item)
            self.component_rects[name] = rect_item
        
        self._render_connections(data_model, show_all_connections, selected_component_name)

    def _render_connections(self, data_model, show_all, selected_name):
        color_output = QColor("#e06c75")
        color_input = QColor("#98c379")
        color_inout = QColor("#61afef")

        all_edges = []
        drawn_pairs = set()
        for source, details in data_model.components.items():
            for conn in details['connections'].get('output', []):
                target = conn['name']
                pair = tuple(sorted((source, target)))
                if pair not in drawn_pairs:
                    all_edges.append({'source': source, 'target': target, 'type': 'output'})
                    drawn_pairs.add(pair)
            for conn in details['connections'].get('inout', []):
                target = conn['name']
                pair = tuple(sorted((source, target)))
                if pair not in drawn_pairs:
                    all_edges.append({'source': source, 'target': target, 'type': 'inout'})
                    drawn_pairs.add(pair)

        for edge in all_edges:
            source, target, conn_type = edge['source'], edge['target'], edge['type']
            if source not in self.component_rects or target not in self.component_rects:
                continue

            start_item = self.component_rects[source]
            end_item = self.component_rects[target]

            to_draw = False
            color = QColor()
            is_bidirectional = False

            if show_all:
                to_draw = True
                is_bidirectional = (conn_type == 'inout')
                color = color_inout if is_bidirectional else color_output
            elif selected_name and (source == selected_name or target == selected_name):
                to_draw = True
                is_bidirectional = (conn_type == 'inout')
                if is_bidirectional:
                    color = color_inout
                else:
                    color = color_output if source == selected_name else color_input

            if to_draw:
                arrow = ArrowItem(start_item, end_item, color, source, target, is_bidirectional)
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
        item_at_pos = self.itemAt(event.pos())
        if not item_at_pos and 'idle' in self.current_mode:
            self.component_clicked.emit(None)
            
        pos = self.mapToScene(event.pos())
        if 'drawing_box' in self.current_mode and event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = pos
            rect_item = ComponentRectItem(QRectF(self.start_pos, self.start_pos))
            rect_item.setPen(QPen(Qt.GlobalColor.cyan, 2, Qt.PenStyle.DashLine))
            self.temp_rect = rect_item
            self.scene.addItem(self.temp_rect)
        elif 'connect' in self.current_mode:
            component_name = self.get_component_name_at(pos)
            self.component_clicked.emit(component_name)
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
            # The calling function in MainWindow will handle setting mode
        else: super().mouseReleaseEvent(event)
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image_item:
            self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)