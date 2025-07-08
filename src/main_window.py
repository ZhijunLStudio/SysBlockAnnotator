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

    # --- THIS METHOD ENABLES TAB CYCLING ---
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_operation()
        # Check if we are in focus mode (show selected only)
        elif not self.show_all_connections:
            if event.key() == Qt.Key.Key_Tab:
                self.cycle_component_selection(forward=True)
                event.accept() # Prevent default Tab behavior
                return
            elif event.key() == Qt.Key.Key_Backtab: # This is Shift+Tab
                self.cycle_component_selection(forward=False)
                event.accept() # Prevent default Shift+Tab behavior
                return
        
        # If not handled, pass to the base class
        super().keyPressEvent(event)

    def _cancel_operation(self):
        if self.connection_start_node:
            # Clearing the scene selection is the correct way to deselect
            self.image_viewer.scene.clearSelection()
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
        self.right_panel.component_selected.connect(self.on_component_selected_from_list)
        self.right_panel.component_delete_requested.connect(self.handle_component_deletion)
        self.right_panel.component_name_changed.connect(self.on_component_name_changed)
        self.right_panel.component_connections_changed.connect(self.on_component_connections_changed)

        # Image Viewer
        self.image_viewer.box_drawn.connect(self.on_box_drawn)
        self.image_viewer.connect_mode_clicked.connect(self.handle_connect_mode_click)
        self.image_viewer.scene_selection_changed.connect(self._handle_scene_selection_change)
        self.image_viewer.selection_deleted.connect(self.handle_canvas_deletion)

    def set_mode(self, mode, force=False):
        if not force and self.current_mode != 'idle':
            self._cancel_operation()
        
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

    def handle_connect_mode_click(self, component_name):
        if '_source' in self.current_mode:
            if not component_name:
                self._cancel_operation()
                return
            self.connection_start_node = component_name
            self.current_mode = self.current_mode.replace('_source', '_target')
            # Programmatically select the item to give visual feedback
            if component_name in self.image_viewer.component_rects:
                self.image_viewer.component_rects[component_name].setSelected(True)
            self.statusBar().showMessage(f"Source: '{component_name}'. Click the TARGET component.")
        elif '_target' in self.current_mode:
            if component_name and component_name != self.connection_start_node:
                self.create_connection(self.connection_start_node, component_name)
            else:
                self.statusBar().showMessage("Invalid target or same as source. Canceled.", 2000)
            self._cancel_operation()

    def create_connection(self, source, target):
        conn_type = 'output' if 'unidirectional' in self.current_mode else 'inout'
        self.data_model.add_connection(source, target, conn_type)
        self._update_all_views() # Data model changed, do a full update

    def _handle_scene_selection_change(self):
        selected_items = self.image_viewer.scene.selectedItems()
        new_selected_name = None
        # Ensure we only care about ComponentRectItem selections
        if selected_items and isinstance(selected_items[0], ComponentRectItem):
            new_selected_name = selected_items[0].data(0)

        if self.selected_component == new_selected_name:
            return

        self.selected_component = new_selected_name
        self._update_ui_for_selection_change()

    def on_component_selected_from_list(self, name):
        if self.selected_component == name:
            return
        
        # Clear previous selection in the scene
        self.image_viewer.scene.clearSelection()

        # Programmatically select the new item in the scene
        if name and name in self.image_viewer.component_rects:
            self.image_viewer.component_rects[name].setSelected(True)
            # This action will trigger _handle_scene_selection_change, which is the single source of truth

    def on_toggle_connections_view(self):
        self.show_all_connections = not self.show_all_connections
        # If entering focus mode without a selection, select the first component
        if not self.show_all_connections and not self.selected_component and self.data_model.components:
            # Use the cycle function to select the first item
            self.cycle_component_selection(forward=True)
        else:
            # Just update the connections view
            self.image_viewer.redraw_connections(self.data_model, self.show_all_connections, self.selected_component)
        self.update_button_states()
    
    def on_skip_image(self):
        dialog = SkipReasonDialog(self)
        reason = dialog.get_reason()
        if reason:
            self.data_model.clear()
            self.data_model.skipped_reason = reason
            self.save_current_annotations()
            self.go_to_next_image()

    # --- THIS METHOD IMPLEMENTS THE CYCLING LOGIC ---
    def cycle_component_selection(self, forward=True):
        # Get the ordered list of component names from the right panel's model
        list_widget = self.right_panel.comp_list_widget
        comp_names = [list_widget.item(i).text() for i in range(list_widget.count())]
        
        if not comp_names:
            return

        try:
            # Find the index of the currently selected component
            current_idx = comp_names.index(self.selected_component)
            # Calculate the next index, wrapping around if necessary
            if forward:
                new_idx = (current_idx + 1) % len(comp_names)
            else:
                new_idx = (current_idx - 1 + len(comp_names)) % len(comp_names)
        except ValueError:
            # If nothing is selected, or selection is invalid, start from the first/last item
            new_idx = 0 if forward else -1

        # Select the new component from the list
        self.on_component_selected_from_list(comp_names[new_idx])

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
        comp_to_delete, did_delete_arrow = None, False
        for item in selected_items:
            if isinstance(item, ComponentRectItem) and item.data(0):
                comp_to_delete = item.data(0)
                break 
            elif isinstance(item, ArrowItem):
                self.data_model.remove_connection(item.source_name, item.target_name, item.conn_type)
                did_delete_arrow = True
        
        if comp_to_delete:
            self.handle_component_deletion(comp_to_delete)
        elif did_delete_arrow:
            self._update_all_views()

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
                self._update_all_views() # Full update because data changed
                self.on_component_selected_from_list(name) # Select the new component
            except ValueError as e:
                QMessageBox.critical(self, "Error", str(e))
        else:
            self._update_all_views() # Redraw to clear any temp items

    def on_component_name_changed(self, old_name, new_name):
        try:
            self.data_model.rename_component(old_name, new_name)
            self.selected_component = new_name # Manually update state
            self._update_all_views()
        except ValueError as e:
            QMessageBox.critical(self, "Rename Error", str(e))
            self._update_ui_for_selection_change()

    def on_component_connections_changed(self, comp_name, conn_type, new_value_str):
        self.data_model.update_connections_from_string(comp_name, conn_type, new_value_str)
        self._update_all_views()

    def handle_component_deletion(self, name):
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Delete component '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
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
        """Full update. Call when data model changes (add/delete/rename/edit)."""
        # Redraw component rects from scratch
        self.image_viewer.redraw_component_rects(self.data_model)
        # Update component list in the right panel
        self.right_panel.update_component_list(self.data_model.components.keys())

        # If the selected component was deleted, reset selection
        if self.selected_component and self.selected_component not in self.data_model.components:
             self.selected_component = None
        
        # Programmatically re-select the current item in the scene, if any
        if self.selected_component:
            if self.selected_component in self.image_viewer.component_rects:
                self.image_viewer.component_rects[self.selected_component].setSelected(True)
        
        # Finally, update all UI elements based on the current (possibly new) selection
        self._update_ui_for_selection_change()
        self.update_button_states()

    def _update_ui_for_selection_change(self):
        """Lightweight update. Call when only the component selection changes."""
        # Update details panel and right list widget selection
        if self.selected_component and self.selected_component in self.data_model.components:
            self.right_panel.update_details(self.selected_component, self.data_model.components[self.selected_component])
            items = self.right_panel.comp_list_widget.findItems(self.selected_component, Qt.MatchFlag.MatchExactly)
            if items and not items[0].isSelected():
                # Block signals to prevent a feedback loop with on_component_selected_from_list
                self.right_panel.comp_list_widget.blockSignals(True)
                self.right_panel.comp_list_widget.setCurrentItem(items[0])
                self.right_panel.comp_list_widget.blockSignals(False)
        else:
            self.right_panel.update_details(None, None)
            self.right_panel.comp_list_widget.clearSelection()

        # Redraw only the connection arrows
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
        self.left_panel.btn_skip.setEnabled(has_images and is_idle)

    def closeEvent(self, event):
        self.save_current_annotations()
        event.accept()