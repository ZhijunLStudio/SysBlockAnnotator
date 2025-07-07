# src/main_window.py
import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox, QSplitter
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeyEvent

from src.data_model import AnnotationData
from src.image_viewer import ImageViewer
from src.widgets.left_panel import LeftPanel
from src.widgets.right_panel import RightPanel
from src.dialogs import ComponentNameDialog, SkipReasonDialog
from src.stylesheet import STYLE_SHEET
from src.drawing_items import ArrowItem
from src.widgets.base_items import ComponentRectItem

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Block Diagram Annotation Tool")
        self.setGeometry(100, 100, 1800, 1000)

        # State
        self.image_folder, self.json_folder = None, None
        self.current_image_path = None
        self.data_model = AnnotationData()
        self.current_mode = 'idle'
        self.selected_component = None
        self.connection_start_node = None
        self.show_all_connections = True 

        # UI
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
        self.splitter.setSizes([250, 1300, 300])
        self.main_layout.addWidget(self.splitter)
        
        self.setStyleSheet(STYLE_SHEET)
        self._create_actions()
        self._connect_signals()
        self.update_button_states()

    def _create_actions(self):
        self.prev_action = QAction("Previous", self); self.prev_action.setShortcut(Qt.Key.Key_A); self.prev_action.triggered.connect(self.go_to_prev_image)
        self.next_action = QAction("Next", self); self.next_action.setShortcut(Qt.Key.Key_D); self.next_action.triggered.connect(self.go_to_next_image)
        self.toggle_view_action = QAction("Toggle View", self); self.toggle_view_action.setShortcut(Qt.Key.Key_V); self.toggle_view_action.triggered.connect(self.on_toggle_connections_view)
        self.addActions([self.prev_action, self.next_action, self.toggle_view_action])

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_operation()
        # --- New: Tab/Shift+Tab for component cycling in focused view ---
        elif event.key() == Qt.Key.Key_Tab:
            if not self.show_all_connections:
                self.cycle_component_selection(forward=True)
        elif event.key() == Qt.Key.Key_Backtab: # Shift+Tab
            if not self.show_all_connections:
                self.cycle_component_selection(forward=False)
        else:
            super().keyPressEvent(event)

    def _cancel_operation(self):
        if self.connection_start_node:
            self.image_viewer.highlight_component_rect(self.connection_start_node, False)
            self.connection_start_node = None
        if self.current_mode != 'idle':
            self.set_mode('idle', force=True)
            self.statusBar().showMessage("Operation Canceled", 2000)

    def _connect_signals(self):
        # Left Panel
        self.left_panel.mode_changed.connect(self.set_mode)
        self.left_panel.load_images_requested.connect(self.load_image_folder)
        self.left_panel.load_jsons_requested.connect(self.load_json_folder)
        self.left_panel.save_requested.connect(self.save_current_annotations)
        self.left_panel.prev_image_requested.connect(self.go_to_prev_image)
        self.left_panel.next_image_requested.connect(self.go_to_next_image)
        self.left_panel.skip_image_requested.connect(self.on_skip_image)
        self.left_panel.toggle_connections_view_requested.connect(self.on_toggle_connections_view)
        
        # Right Panel
        self.right_panel.file_selected.connect(self.on_file_selected)
        self.right_panel.component_selected.connect(self.on_component_selected)
        self.right_panel.component_delete_requested.connect(self.handle_component_deletion)
        self.right_panel.component_name_changed.connect(self.on_component_name_changed)
        self.right_panel.component_connections_changed.connect(self.on_component_connections_changed)

        # Image Viewer
        self.image_viewer.box_drawn.connect(self.on_box_drawn)
        self.image_viewer.component_clicked.connect(self.handle_canvas_click)
        self.image_viewer.selection_deleted.connect(self.handle_canvas_deletion)

    def set_mode(self, mode, force=False):
        if not force and self.current_mode != 'idle':
            self._cancel_operation()
            return
        
        self.current_mode = mode
        if self.current_mode.startswith('connect'):
            self.current_mode = f"{mode}_source"
            self.statusBar().showMessage(f"CONNECT MODE: Click the SOURCE component. (Press Esc to cancel)")
        elif self.current_mode == 'drawing_box':
             self.statusBar().showMessage(f"DRAW MODE: Draw a box for a new component. (Press Esc to cancel)")
        elif self.current_mode == 'idle':
             self.statusBar().showMessage("Ready")

        self.image_viewer.set_mode(self.current_mode, force=force)
        self.update_button_states()

    def handle_canvas_click(self, component_name):
        mode = self.current_mode
        
        if not component_name and 'connect' in mode:
            self._cancel_operation()
            return

        if 'idle' in mode:
            self.on_component_selected(component_name)
        elif 'drawing_box' in mode:
             self.on_component_selected(component_name)
        elif '_source' in mode:
            if component_name:
                self.connection_start_node = component_name
                self.current_mode = mode.replace('_source', '_target')
                self.image_viewer.highlight_component_rect(component_name, True)
                self.statusBar().showMessage(f"Source: '{component_name}'. Click the TARGET component.")
        elif '_target' in mode:
            if component_name and component_name != self.connection_start_node:
                self.create_connection(self.connection_start_node, component_name)
            else:
                self.statusBar().showMessage("Invalid target or same as source. Canceled.", 2000)
            self._cancel_operation()

    def create_connection(self, source, target):
        conn_type = 'output' if 'unidirectional' in self.current_mode else 'inout'
        self.data_model.add_connection(source, target, conn_type)
        self.statusBar().showMessage(f"Success: Created {conn_type} connection.", 3000)
        self._update_all_views()

    def on_component_selected(self, name):
        if self.selected_component:
            self.image_viewer.highlight_component_rect(self.selected_component, False)
        
        # If clicked component is different from current, select it.
        # If clicked is same, it remains selected.
        # If clicked is None, deselect.
        self.selected_component = name
        self._update_all_views()

    def on_toggle_connections_view(self):
        self.show_all_connections = not self.show_all_connections
        # If entering focused view without a selection, select the first component
        if not self.show_all_connections and not self.selected_component and self.data_model.components:
            first_comp = sorted(self.data_model.components.keys())[0]
            self.on_component_selected(first_comp)
        else:
            self._update_all_views()

    def on_skip_image(self):
        dialog = SkipReasonDialog(self)
        reason = dialog.get_reason()
        if reason:
            self.data_model.clear()
            self.data_model.skipped_reason = reason
            self.save_current_annotations()
            self.go_to_next_image()

    def cycle_component_selection(self, forward=True):
        comp_names = sorted(list(self.data_model.components.keys()))
        if not comp_names: return

        if self.selected_component not in comp_names:
            new_idx = 0
        else:
            current_idx = comp_names.index(self.selected_component)
            if forward:
                new_idx = (current_idx + 1) % len(comp_names)
            else:
                new_idx = (current_idx - 1 + len(comp_names)) % len(comp_names)
        
        self.on_component_selected(comp_names[new_idx])

    def go_to_prev_image(self):
        idx = self.right_panel.get_current_file_index()
        if idx > 0:
            item = self.right_panel.file_list_widget.item(idx - 1)
            self.on_file_selected(item)

    def go_to_next_image(self):
        idx, count = self.right_panel.get_current_file_index(), self.right_panel.get_file_count()
        if idx < count - 1:
            item = self.right_panel.file_list_widget.item(idx + 1)
            self.on_file_selected(item)
            
    def handle_canvas_deletion(self, selected_items):
        comp_to_delete = None
        did_delete_arrow = False
        for item in selected_items:
            if isinstance(item, ComponentRectItem) and item.data(0):
                comp_to_delete = item.data(0)
                break 
            elif isinstance(item, ArrowItem):
                self.data_model.remove_connection(item.source_name, item.target_name, item.conn_type)
                did_delete_arrow = True
        
        if comp_to_delete: self.handle_component_deletion(comp_to_delete)
        elif did_delete_arrow: self._update_all_views()

    def load_image_folder(self, folder_path):
        self.image_folder = folder_path
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        self.right_panel.update_file_list(files)
        if files: 
            self.on_file_selected(self.right_panel.file_list_widget.item(0))
        self.update_button_states()

    def on_file_selected(self, item):
        if not item or not self.image_folder: return
        
        # Save previous work before switching
        if self.current_image_path:
            self.save_current_annotations()
        
        self._cancel_operation() # Reset mode to idle
        new_path = os.path.join(self.image_folder, item.text())
        if new_path == self.current_image_path: return

        self.current_image_path = new_path
        self.selected_component = None
        self.right_panel.file_list_widget.setCurrentItem(item)
        
        self.data_model.clear()
        self.image_viewer.set_image(self.current_image_path)
        self._load_annotations_for_current_image()
        self._update_all_views()

    def _load_annotations_for_current_image(self):
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
                self.on_component_selected(name) # Select the new component
            except ValueError as e:
                QMessageBox.critical(self, "Error", str(e))
        else:
            self._update_all_views() # Redraw to remove temp items if canceled

    def on_component_name_changed(self, old_name, new_name):
        try:
            self.data_model.rename_component(old_name, new_name)
            self.selected_component = new_name # Update selection to new name
            self._update_all_views()
        except ValueError as e:
            QMessageBox.critical(self, "Rename Error", str(e))
            # Revert the edit box text
            self.right_panel.name_edit.setText(old_name)

    def on_component_connections_changed(self, comp_name, conn_type, new_value_str):
        self.data_model.update_connections_from_string(comp_name, conn_type, new_value_str)
        self._update_all_views()

    def handle_component_deletion(self, name):
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Delete component '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.selected_component == name: self.selected_component = None
            self.data_model.remove_component(name)
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
        # Update component list
        comp_names = self.data_model.components.keys()
        self.right_panel.update_component_list(comp_names)
        
        # Update details panel
        if self.selected_component and self.selected_component in self.data_model.components:
            details = self.data_model.components[self.selected_component]
            self.right_panel.update_details(self.selected_component, details)
        else:
            self.right_panel.update_details(None, None)
        
        # Update graphics view
        self.image_viewer.update_annotations(self.data_model, self.show_all_connections, self.selected_component)
        
        # Sync list selection and graphic highlight
        if self.selected_component:
            self.image_viewer.highlight_component_rect(self.selected_component, True)
            items = self.right_panel.comp_list_widget.findItems(self.selected_component, Qt.MatchFlag.MatchExactly)
            if items:
                self.right_panel.comp_list_widget.setCurrentItem(items[0])
        else:
            self.right_panel.comp_list_widget.clearSelection()

        self.update_button_states()
        
    def update_button_states(self):
        has_images = self.right_panel.get_file_count() > 0
        is_idle = 'idle' in self.current_mode
        
        # Annotation tools enabled if image is loaded and mode is idle
        self.left_panel.btn_connect_uni.setEnabled(has_images and is_idle)
        self.left_panel.btn_connect_bi.setEnabled(has_images and is_idle)
        self.left_panel.btn_draw_box.setEnabled(has_images and is_idle)
        self.left_panel.btn_toggle_connections.setEnabled(has_images)
        self.left_panel.update_toggle_button_text(self.show_all_connections)
        
        # Navigation
        idx, count = self.right_panel.get_current_file_index(), self.right_panel.get_file_count()
        self.left_panel.btn_prev.setEnabled(idx > 0 and is_idle)
        self.left_panel.btn_next.setEnabled(idx < count - 1 and is_idle)
        self.left_panel.btn_skip.setEnabled(has_images and is_idle)

    def closeEvent(self, event):
        self.save_current_annotations()
        event.accept()