# src/image_viewer.py
import math
from collections import defaultdict
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPen, QColor, QPainter, QFont

from src.widgets.base_items import ComponentRectItem
from src.drawing_items import ArrowItem

class ImageViewer(QGraphicsView):
    # --- NO CHANGES to signals ---
    box_drawn = pyqtSignal(QRectF)
    scene_selection_changed = pyqtSignal()
    connect_mode_clicked = pyqtSignal(str)
    idle_mode_clicked = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.scene.selectionChanged.connect(self.scene_selection_changed)
        self.setScene(self.scene)
        
        self.image_item = None
        self.skipped_text_item = None
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
    
    # --- NO CHANGES to most methods ---
    def set_image(self, image_path):
        if self.image_item: self.scene.removeItem(self.image_item); self.image_item = None
        pixmap = QPixmap(image_path)
        if pixmap.isNull(): return
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)

    def clear_all_annotations(self):
        self._clear_items(ComponentRectItem)
        self._clear_items(ArrowItem)
        if self.skipped_text_item: self.scene.removeItem(self.skipped_text_item); self.skipped_text_item = None
        self.component_rects.clear()

    def show_skipped_overlay(self, reason):
        self.clear_all_annotations()
        if not self.image_item: return
        font = QFont("Arial", 50, QFont.Weight.Bold)
        self.skipped_text_item = QGraphicsTextItem(f"SKIPPED\nReason: {reason}")
        self.skipped_text_item.setFont(font)
        self.skipped_text_item.setDefaultTextColor(QColor(255, 0, 0, 150))
        img_rect = self.image_item.boundingRect()
        text_rect = self.skipped_text_item.boundingRect()
        x = img_rect.center().x() - text_rect.width() / 2
        y = img_rect.center().y() - text_rect.height() / 2
        self.skipped_text_item.setPos(x, y)
        self.scene.addItem(self.skipped_text_item)

    def _clear_items(self, item_type):
        items_to_remove = [item for item in self.scene.items() if isinstance(item, item_type)]
        for item in items_to_remove: self.scene.removeItem(item)

    def set_mode(self, mode, force=False):
        self.current_mode = mode
        if 'drawing_box' in mode:
            self.setDragMode(self.DragMode.NoDrag); self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        elif 'connect' in mode:
            self.setDragMode(self.DragMode.NoDrag); self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setDragMode(self.DragMode.ScrollHandDrag); self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def redraw_component_rects(self, data_model):
        self.clear_all_annotations()
        if not data_model: return
        for name, details in data_model.components.items():
            box = details['component_box']
            rect = QRectF(box[0], box[1], box[2] - box[0], box[3] - box[1])
            rect_item = ComponentRectItem(rect)
            rect_item.setData(0, name)
            self.scene.addItem(rect_item)
            self.component_rects[name] = rect_item

    # ##################################################################
    # #         --- MODIFICATION: Complete Rewrite of Drawing Logic ---#
    # ##################################################################
    def redraw_connections(self, data_model, show_all, selected_name, problem_connections):
        self._clear_items(ArrowItem)
        if not data_model or not self.component_rects: return
        
        color_output = QColor("#e06c75")
        color_input = QColor("#98c379")
        color_inout = QColor("#61afef")
        color_problem = QColor("#d19a66") # Bright Orange

        # Step 1: Build a complete, unified map of all connections
        all_connections = defaultdict(lambda: {'type': 'none', 'count': 0})

        for source_name, details in data_model.components.items():
            connections = details.get("connections", {})
            
            # Process outputs
            for conn in connections.get("output", []):
                target_name = conn['name']
                pair = (source_name, target_name)
                all_connections[pair]['type'] = 'output'
                all_connections[pair]['count'] = conn.get('count', 1)

            # Process inputs (to find connections missed by output)
            for conn in connections.get("input", []):
                target_name = conn['name'] # Here, target is the source of the connection
                pair = (target_name, source_name)
                # Only add if it doesn't already exist as an output
                if all_connections[pair]['type'] == 'none':
                    all_connections[pair]['type'] = 'output' # It's an output from target to source
                    # The count isn't specified on input, so default to 1
                    all_connections[pair]['count'] = 1 
            
            # Process inouts
            for conn in connections.get("inout", []):
                target_name = conn['name']
                # Use a sorted tuple to represent the undirected pair
                pair = tuple(sorted((source_name, target_name)))
                all_connections[pair]['type'] = 'inout'
                # For inout, counts can be on either side, take the max
                all_connections[pair]['count'] = max(
                    all_connections[pair]['count'], conn.get('count', 1)
                )

        # Step 2: Iterate through the unified map and draw
        for pair, info in all_connections.items():
            conn_type = info['type']
            if conn_type == 'none': continue

            source, target = pair[0], pair[1]
            if conn_type == 'inout': # The pair was sorted for uniqueness
                source, target = pair[0], pair[1]
            
            # Skip if components don't exist on the canvas
            if source not in self.component_rects or target not in self.component_rects:
                continue

            # Determine visibility and color
            is_bidirectional = (conn_type == 'inout')
            is_problem = (source, target, conn_type) in problem_connections or \
                         (target, source, conn_type) in problem_connections
            
            draw_this_arrow = False
            final_color = QColor()
            
            if is_problem:
                draw_this_arrow, final_color = True, color_problem
            elif show_all:
                draw_this_arrow, final_color = True, color_inout if is_bidirectional else color_output
            elif selected_name and (source == selected_name or target == selected_name):
                draw_this_arrow, final_color = True, color_inout if is_bidirectional else (color_output if source == selected_name else color_input)

            # Step 3: Draw the arrow if it's visible
            if draw_this_arrow:
                start_item = self.component_rects[source]
                end_item = self.component_rects[target]
                count = info['count']

                line_width = 5 if is_problem or not show_all else 3
                line_vec = end_item.sceneBoundingRect().center() - start_item.sceneBoundingRect().center()
                if line_vec.isNull(): continue
                perp_vec = QPointF(line_vec.y(), -line_vec.x())
                norm_perp = perp_vec / math.sqrt(QPointF.dotProduct(perp_vec, perp_vec)) if not perp_vec.isNull() else QPointF()
                
                for i in range(count):
                    offset = norm_perp * ((i - (count - 1) / 2.0) * 15.0)
                    arrow = ArrowItem(start_item, end_item, final_color, source, target, is_bidirectional, offset=offset, line_width=line_width)
                    self.scene.addItem(arrow)


    # --- NO CHANGES to mouse events or resizeEvent ---
    def mousePressEvent(self, event):
        if self.skipped_text_item and self.skipped_text_item.isVisible(): super().mousePressEvent(event); return
        if 'drawing_box' in self.current_mode and event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = self.mapToScene(event.pos())
            rect_item = ComponentRectItem(QRectF(self.start_pos, self.start_pos)); rect_item.setPen(QPen(Qt.GlobalColor.cyan, 2, Qt.PenStyle.DashLine)); self.temp_rect = rect_item; self.scene.addItem(self.temp_rect); return
        items_at_pos = self.items(event.pos())
        if 'connect' in self.current_mode:
            component_items_at_pos = [item for item in items_at_pos if isinstance(item, ComponentRectItem)]
            if component_items_at_pos: component_items_at_pos.sort(key=lambda item: item.rect().width() * item.rect().height()); self.connect_mode_clicked.emit(component_items_at_pos[0].data(0))
            else: self.connect_mode_clicked.emit(None)
            return
        if 'idle' in self.current_mode:
            if any(isinstance(item, ArrowItem) for item in items_at_pos): super().mousePressEvent(event); return
            component_items_at_pos = [item for item in items_at_pos if isinstance(item, ComponentRectItem)]
            self.idle_mode_clicked.emit(component_items_at_pos); super().mousePressEvent(event); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if 'drawing_box' in self.current_mode and self.start_pos and self.temp_rect: self.temp_rect.setRect(QRectF(self.start_pos, self.mapToScene(event.pos())).normalized())
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if 'drawing_box' in self.current_mode and self.start_pos and self.temp_rect:
            rect = self.temp_rect.rect()
            if self.temp_rect.scene(): self.scene.removeItem(self.temp_rect)
            if rect.width() > 5 and rect.height() > 5: self.box_drawn.emit(rect)
            self.temp_rect, self.start_pos = None, None
        else: super().mouseReleaseEvent(event)
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image_item: self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)