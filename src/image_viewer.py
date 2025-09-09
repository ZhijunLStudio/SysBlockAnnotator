import math
from collections import defaultdict
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPen, QColor, QPainter, QFont

from src.widgets.base_items import ComponentRectItem
from src.drawing_items import ArrowItem

class ImageViewer(QGraphicsView):
    # --- 信号部分无变化 ---
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
    
    # --- 其他大部分方法无变化 ---
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

    ##################################################################
    #         --- 带新颜色方案的连接绘制逻辑 ---#
    ##################################################################
    def redraw_connections(self, data_model, show_all, selected_name):
        self._clear_items(ArrowItem)
        if not data_model or not self.component_rects:
            return

        # 步骤 1: 统一收集所有连接
        all_connections = []
        processed_inout_pairs = set()

        for comp_name, details in data_model.components.items():
            connections = details.get("connections", {})
            
            # 处理 'input' (箭头指向当前组件)
            for conn in connections.get("input", []):
                all_connections.append({
                    'source': conn.get('name'),
                    'target': comp_name,
                    'status': conn.get('status'),
                    'is_bidirectional': False
                })

            # 处理 'output' (箭头从当前组件出发)
            for conn in connections.get("output", []):
                all_connections.append({
                    'source': comp_name,
                    'target': conn.get('name'),
                    'status': conn.get('status'),
                    'is_bidirectional': False
                })

            # 处理 'inout' (双向), 并避免重复
            for conn in connections.get("inout", []):
                target_name = conn.get('name')
                pair = tuple(sorted((comp_name, target_name)))
                if pair not in processed_inout_pairs:
                    processed_inout_pairs.add(pair)
                    all_connections.append({
                        'source': comp_name,
                        'target': target_name,
                        'status': conn.get('status'),
                        'is_bidirectional': True
                    })

        # 步骤 2: 按物理连接对进行分组，以便处理偏移
        connection_groups = defaultdict(list)
        for conn_info in all_connections:
            source_name = conn_info.get('source')
            target_name = conn_info.get('target')

            # 过滤掉不存在的组件连接
            if source_name not in self.component_rects or target_name not in self.component_rects:
                continue
                
            pair = tuple(sorted((source_name, target_name)))
            connection_groups[pair].append(conn_info)

        # 步骤 3: 遍历分组并绘制所有箭头
        for pair, conn_list in connection_groups.items():
            count = len(conn_list)
            
            p1_name, p2_name = pair
            start_item = self.component_rects[p1_name]
            end_item = self.component_rects[p2_name]

            # 计算用于偏移的垂直向量
            line_vec = end_item.sceneBoundingRect().center() - start_item.sceneBoundingRect().center()
            if line_vec.isNull(): continue
            perp_vec = QPointF(line_vec.y(), -line_vec.x())
            norm_perp = perp_vec / math.sqrt(QPointF.dotProduct(perp_vec, perp_vec)) if not perp_vec.isNull() else QPointF()

            for i, conn_info in enumerate(conn_list):
                # 确定是否应绘制此箭头
                should_draw = show_all or (selected_name and (conn_info['source'] == selected_name or conn_info['target'] == selected_name))
                if not should_draw:
                    continue

                # **核心修改: 根据您的新规则设置颜色**
                status = conn_info.get('status')
                is_bidirectional = conn_info.get('is_bidirectional')
                
                final_color = QColor()
                # 优先级 1 & 2: 错误状态优先
                if status == "WRONG_PREDICTION":
                    final_color = QColor("#e5c07b")  # 黄色
                elif status == "MISSED_GROUND_TRUTH":
                    final_color = QColor("#c678dd")  # 紫色
                # 优先级 3: 正常连接的类型
                elif is_bidirectional:
                    final_color = QColor("#61afef")  # 蓝色 (正常的inout)
                elif status == "CORRECT":
                    final_color = QColor("#98c379")  # 绿色 (正确的单向)
                # 备用颜色
                else:
                    final_color = QColor("#abb2bf")  # 灰色 (用于未知状态)

                line_width = 5 if not show_all else 3
                # 为平行线计算偏移量
                offset = norm_perp * ((i - (count - 1) / 2.0) * 15.0)

                arrow_source_item = self.component_rects[conn_info['source']]
                arrow_target_item = self.component_rects[conn_info['target']]

                arrow = ArrowItem(
                    start_item=arrow_source_item,
                    end_item=arrow_target_item,
                    color=final_color,
                    source_name=conn_info['source'],
                    target_name=conn_info['target'],
                    is_bidirectional=conn_info['is_bidirectional'],
                    offset=offset,
                    line_width=line_width
                )
                self.scene.addItem(arrow)

    # --- 鼠标事件和resizeEvent无变化 ---
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