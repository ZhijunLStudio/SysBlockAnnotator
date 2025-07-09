# src/main_window.py
import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox, QSplitter
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeyEvent

from src.data_model import AnnotationData
from src.image_viewer import ImageViewer
from src.widgets.left_panel import LeftPanel
from src.widgets.right_panel import RightPanel
from src.dialogs import ComponentNameDialog
from src.stylesheet import STYLE_SHEET
from src.drawing_items import ArrowItem
from src.widgets.base_items import ComponentRectItem

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Block Diagram Annotation Tool")
        self.setGeometry(100, 100, 1800, 1000)
        
        self.image_folder, self.json_folder = None, None
        self.current_image_path = None
        self.data_model = AnnotationData()
        self.current_mode = 'idle'
        self.selected_component = None
        self.connection_start_node = None
        self.show_all_connections = True 

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.statusBar().showMessage("Ready")

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_panel = LeftPanel()
        self.image_viewer = ImageViewer()
        self.right_panel = RightPanel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.image_viewer)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([300, 1200, 300])
        self.main_layout.addWidget(self.splitter)
        
        self.setStyleSheet(STYLE_SHEET)
        self._connect_signals()
        self.update_button_states()
        self.left_panel.toggle_skip_panel(False)
    
    # --- REBUILT: keyPressEvent is now the single source of truth for ALL shortcuts ---
    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        # --- Section 1: Shortcuts that work regardless of the current mode ---
        if key == Qt.Key.Key_Escape:
            self._cancel_operation()
            event.accept()
            return
        
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.handle_deletion()
            event.accept()
            return

        # --- Section 2: Shortcuts that should only work in 'idle' mode ---
        if self.current_mode == 'idle':
            if key == Qt.Key.Key_W:
                # Use .click() to also get the visual feedback on the button
                if self.left_panel.btn_draw_box.isEnabled():
                    self.left_panel.btn_draw_box.click()
            elif key == Qt.Key.Key_O:
                if self.left_panel.btn_connect_uni.isEnabled():
                    self.left_panel.btn_connect_uni.click()
            elif key == Qt.Key.Key_N:
                if self.left_panel.btn_connect_bi.isEnabled():
                    self.left_panel.btn_connect_bi.click()
            elif key == Qt.Key.Key_A:
                if self.left_panel.btn_prev.isEnabled():
                    self.go_to_prev_image()
            elif key == Qt.Key.Key_D:
                if self.left_panel.btn_next.isEnabled():
                    self.go_to_next_image()
            elif key == Qt.Key.Key_V:
                if self.left_panel.btn_toggle_connections.isEnabled():
                    self.on_toggle_connections_view()
            elif key == Qt.Key.Key_Tab and not self.show_all_connections:
                self.cycle_component_selection(forward=True)
            elif key == Qt.Key.Key_Backtab and not self.show_all_connections:
                self.cycle_component_selection(forward=False)
            else:
                # If no shortcut matches, let the base class handle it
                super().keyPressEvent(event)
                return
            
            # If we handled a shortcut, accept the event
            event.accept()
            return

        # --- Section 3: If not in idle mode, let other widgets handle keys, or ignore ---
        super().keyPressEvent(event)

    def _connect_signals(self):
        # We no longer need to connect a deletion signal from ImageViewer
        self.left_panel.mode_changed.connect(self.set_mode)
        self.left_panel.load_images_requested.connect(self.load_image_folder)
        self.left_panel.load_jsons_requested.connect(self.load_json_folder)
        self.left_panel.save_requested.connect(self.save_current_annotations)
        self.left_panel.prev_image_requested.connect(self.go_to_prev_image)
        self.left_panel.next_image_requested.connect(self.go_to_next_image)
        self.left_panel.skip_image_requested.connect(self.on_skip_image)
        self.left_panel.toggle_connections_view_requested.connect(self.on_toggle_connections_view)
        
        self.right_panel.file_selected.connect(self.on_file_selected)
        self.right_panel.component_selected.connect(self.on_component_selected_from_list)
        self.right_panel.component_delete_requested.connect(self.handle_component_deletion)
        self.right_panel.component_name_changed.connect(self.on_component_name_changed)
        self.right_panel.component_connections_changed.connect(self.on_component_connections_changed)

        self.image_viewer.box_drawn.connect(self.on_box_drawn)
        self.image_viewer.connect_mode_clicked.connect(self.handle_connect_mode_click)
        self.image_viewer.scene_selection_changed.connect(self._handle_scene_selection_change)
        self.image_viewer.idle_mode_clicked.connect(self.handle_idle_mode_click)

    # --- NEW: Central deletion handler ---
    def handle_deletion(self):
        selected_items = self.image_viewer.scene.selectedItems()
        if not selected_items:
            return

        comp_to_delete, did_delete_arrow = None, False
        for item in selected_items:
            if isinstance(item, ComponentRectItem) and item.data(0):
                comp_to_delete = item.data(0)
                break 
            elif isinstance(item, ArrowItem):
                self.data_model.remove_connection(item.source_name, item.target_name, item.conn_type)
                did_delete_arrow = True
        
        # Prioritize deleting components over arrows if both are selected
        if comp_to_delete:
            self.handle_component_deletion(comp_to_delete)
        elif did_delete_arrow:
            # This is a data model change, so a full but safe update is needed.
            self._update_all_views()

    def handle_component_deletion(self, name):
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Delete component '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # This is the key change: Block signals that could cause re-entry issues
            self.image_viewer.scene.blockSignals(True)
            self.data_model.remove_component(name)
            self._update_all_views() # This will redraw everything safely
            self.image_viewer.scene.blockSignals(False)

    # ... (the rest of the file is the same as the previous correct version) ...
    def _cancel_operation(self):
        if self.connection_start_node:
            self.image_viewer.scene.clearSelection()
            self.connection_start_node = None
        if self.current_mode != 'idle':
            self.set_mode('idle', force=True)
            self.statusBar().showMessage("Operation Canceled", 2000)

    def set_mode(self, mode, force=False):
        if not force and self.current_mode != 'idle': self._cancel_operation()
        self.current_mode = mode
        if self.current_mode.startswith('connect'):
            self.current_mode = f"{mode}_source"
            self.statusBar().showMessage(f"CONNECT MODE: Click the SOURCE component. (Press Esc to cancel)")
        elif self.current_mode == 'drawing_box':
             self.statusBar().showMessage(f"DRAW MODE: Draw a box for a new component. (Press Esc to cancel)")
        elif self.current_mode == 'idle': self.statusBar().showMessage("Ready")
        self.image_viewer.set_mode(self.current_mode, force=force)
        self.update_button_states()

    def handle_connect_mode_click(self, component_name):
        if '_source' in self.current_mode:
            if not component_name: self._cancel_operation(); return
            self.connection_start_node = component_name
            self.current_mode = self.current_mode.replace('_source', '_target')
            if component_name in self.image_viewer.component_rects:
                self.image_viewer.component_rects[component_name].setSelected(True)
            self.statusBar().showMessage(f"Source: '{component_name}'. Click the TARGET component.")
        elif '_target' in self.current_mode:
            if component_name and component_name != self.connection_start_node:
                self.create_connection(self.connection_start_node, component_name)
            else: self.statusBar().showMessage("Invalid target or same as source. Canceled.", 2000)
            self._cancel_operation()

    def create_connection(self, source, target):
        conn_type = 'output' if 'unidirectional' in self.current_mode else 'inout'
        self.data_model.add_connection(source, target, conn_type)
        self._update_all_views()

    def handle_idle_mode_click(self, clicked_items):
        self.image_viewer.scene.clearSelection()
        component_items = [item for item in clicked_items if isinstance(item, ComponentRectItem)]
        if not component_items: return
        component_items.sort(key=lambda item: item.rect().width() * item.rect().height())
        item_to_select = component_items[0]
        item_to_select.setSelected(True)

    def _handle_scene_selection_change(self):
        selected_items = self.image_viewer.scene.selectedItems()
        new_selected_name = None
        if selected_items and isinstance(selected_items[0], ComponentRectItem):
            new_selected_name = selected_items[0].data(0)
        if self.selected_component == new_selected_name: return
        self.selected_component = new_selected_name
        self._update_ui_for_selection_change()

    def on_component_selected_from_list(self, name):
        if self.selected_component == name: return
        self.image_viewer.scene.clearSelection()
        if name and name in self.image_viewer.component_rects:
            self.image_viewer.component_rects[name].setSelected(True)

    def on_toggle_connections_view(self):
        self.show_all_connections = not self.show_all_connections
        if not self.show_all_connections and not self.selected_component and self.data_model.components:
            self.cycle_component_selection(forward=True)
        else:
            self.image_viewer.redraw_connections(self.data_model, self.show_all_connections, self.selected_component)
        self.update_button_states()
    
    def on_skip_image(self, reason: str):
        if not reason: return
        if not self.current_image_path:
            QMessageBox.warning(self, "No Image", "Please load an image before skipping.")
            return
        self.data_model.clear()
        self.data_model.skipped_reason = reason
        self.save_current_annotations()
        self.go_to_next_image()

    def cycle_component_selection(self, forward=True):
        list_widget = self.right_panel.comp_list_widget
        comp_names = [list_widget.item(i).text() for i in range(list_widget.count())]
        if not comp_names: return
        try:
            current_idx = comp_names.index(self.selected_component)
            new_idx = (current_idx + (1 if forward else -1)) % len(comp_names)
        except ValueError:
            new_idx = 0 if forward else -1
        self.on_component_selected_from_list(comp_names[new_idx])

    def go_to_prev_image(self):
        if not self.left_panel.btn_prev.isEnabled(): return
        idx = self.right_panel.get_current_file_index()
        if idx > 0:
            item = self.right_panel.file_list_widget.item(idx - 1)
            self.on_file_selected(item)

    def go_to_next_image(self):
        if not self.left_panel.btn_next.isEnabled(): return
        idx, count = self.right_panel.get_current_file_index(), self.right_panel.get_file_count()
        if idx < count - 1:
            item = self.right_panel.file_list_widget.item(idx + 1)
            self.on_file_selected(item)
        else:
            self.statusBar().showMessage("This is the last image.", 3000)

    def load_image_folder(self, folder_path):
        self.image_folder = folder_path
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        self.right_panel.update_file_list(files)
        if files: self.on_file_selected(self.right_panel.file_list_widget.item(0))
        self.update_button_states()

    def on_file_selected(self, item):
        if not item or not self.image_folder: return
        if self.current_image_path: self.save_current_annotations()
        self._cancel_operation()
        new_path = os.path.join(self.image_folder, item.text())
        if new_path == self.current_image_path: return
        self.current_image_path = new_path
        self.right_panel.file_list_widget.setCurrentItem(item)
        self.image_viewer.set_image(self.current_image_path)
        self._load_annotations_for_current_image()
        self._update_all_views()

    def _load_annotations_for_current_image(self):
        self.selected_component = None
        self.data_model.clear()
        if not self.json_folder or not self.current_image_path: return
        base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        json_path = os.path.join(self.json_folder, f"{base_name}.json")
        self.data_model.load_from_json(json_path)

    def on_box_drawn(self, rect):
        self.set_mode('idle', force=True)
        name = ComponentNameDialog(self).get_name()
        if name:
            try:
                self.data_model.add_component(name, rect)
                self._update_all_views()
                self.on_component_selected_from_list(name)
            except ValueError as e: QMessageBox.critical(self, "Error", str(e))
        else: self._update_all_views()

    def on_component_name_changed(self, old_name, new_name):
        try:
            self.data_model.rename_component(old_name, new_name)
            self.selected_component = new_name
            self._update_all_views()
        except ValueError as e:
            QMessageBox.critical(self, "Rename Error", str(e))
            self._update_ui_for_selection_change()

    def on_component_connections_changed(self, comp_name, conn_type, new_value_str):
        self.data_model.update_connections_from_string(comp_name, conn_type, new_value_str)
        self._update_all_views()

    def save_current_annotations(self):
        if not all([self.current_image_path, self.json_folder]): return False
        if not self.data_model.components and not self.data_model.skipped_reason: return False
        base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        json_path = os.path.join(self.json_folder, f"{base_name}.json")
        os.makedirs(self.json_folder, exist_ok=True)
        return self.data_model.save_to_json(json_path)

    def load_json_folder(self, folder_path):
        self.json_folder = folder_path
        if self.current_image_path:
            self._load_annotations_for_current_image()
            self._update_all_views()
        self.update_button_states()
        
    def _update_all_views(self):
        self.image_viewer.redraw_component_rects(self.data_model)
        self.right_panel.update_component_list(self.data_model.components.keys())
        if self.selected_component and self.selected_component not in self.data_model.components:
             self.selected_component = None
        if self.selected_component and self.selected_component in self.image_viewer.component_rects:
            self.image_viewer.component_rects[self.selected_component].setSelected(True)
        self._update_ui_for_selection_change()
        self.update_button_states()

    def _update_ui_for_selection_change(self):
        if self.selected_component and self.selected_component in self.data_model.components:
            self.right_panel.update_details(self.selected_component, self.data_model.components[self.selected_component])
            items = self.right_panel.comp_list_widget.findItems(self.selected_component, Qt.MatchFlag.MatchExactly)
            if items and not items[0].isSelected():
                self.right_panel.comp_list_widget.blockSignals(True)
                self.right_panel.comp_list_widget.setCurrentItem(items[0])
                self.right_panel.comp_list_widget.blockSignals(False)
        else:
            self.right_panel.update_details(None, None)
            self.right_panel.comp_list_widget.clearSelection()
        self.image_viewer.redraw_connections(self.data_model, self.show_all_connections, self.selected_component)
        
    def update_button_states(self):
        has_images = self.right_panel.get_file_count() > 0
        is_idle = 'idle' in self.current_mode
        self.left_panel.btn_connect_uni.setEnabled(has_images and is_idle)
        self.left_panel.btn_connect_bi.setEnabled(has_images and is_idle)
        self.left_panel.btn_draw_box.setEnabled(has_images and is_idle)
        self.left_panel.btn_toggle_connections.setEnabled(has_images)
        self.left_panel.update_toggle_button_text(self.show_all_connections)
        idx, count = self.right_panel.get_current_file_index(), self.right_panel.get_file_count()
        self.left_panel.btn_prev.setEnabled(idx > 0 and is_idle)
        self.left_panel.btn_next.setEnabled(idx < count - 1 and is_idle)
        self.left_panel.toggle_skip_button.setEnabled(has_images)

    def closeEvent(self, event):
        self.save_current_annotations()
        event.accept()