# src/widgets/right_panel.py
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QGroupBox, 
                             QLabel, QSplitter, QListWidgetItem, QMenu,
                             QLineEdit, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', s)]

class RightPanel(QWidget):
    component_selected = pyqtSignal(str)
    component_delete_requested = pyqtSignal(str)
    file_selected = pyqtSignal(QListWidgetItem)
    
    # New signals for editing details
    component_name_changed = pyqtSignal(str, str) # old_name, new_name
    component_connections_changed = pyqtSignal(str, str, str) # name, conn_type, new_value_string

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        # --- Details Group (Rebuilt with QLineEdit for editing) ---
        self.details_group = QGroupBox("Component Details")
        details_layout = QFormLayout()
        details_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        
        self.name_edit = QLineEdit()
        self.inputs_edit = QLineEdit()
        self.outputs_edit = QLineEdit()
        self.inouts_edit = QLineEdit()
        
        self.name_edit.editingFinished.connect(self._on_name_changed)
        self.inputs_edit.editingFinished.connect(lambda: self._on_connections_changed('input'))
        self.outputs_edit.editingFinished.connect(lambda: self._on_connections_changed('output'))
        self.inouts_edit.editingFinished.connect(lambda: self._on_connections_changed('inout'))

        details_layout.addRow("<b style='color:#c678dd;'>Name:</b>", self.name_edit)
        details_layout.addRow("<b style='color:#98c379;'>Inputs:</b>", self.inputs_edit)
        details_layout.addRow("<b style='color:#e06c75;'>Outputs:</b>", self.outputs_edit)
        details_layout.addRow("<b style='color:#61afef;'>In/Outs:</b>", self.inouts_edit)
        
        self.details_group.setLayout(details_layout)
        self._current_comp_name = None
        self._set_details_enabled(False)

        # --- Component List Group ---
        self.comp_list_group = QGroupBox("Annotated Components")
        comp_list_layout = QVBoxLayout()
        self.comp_list_widget = QListWidget()
        self.comp_list_widget.itemClicked.connect(self.on_comp_selected)
        self.comp_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.comp_list_widget.customContextMenuRequested.connect(self.show_comp_context_menu)
        comp_list_layout.addWidget(self.comp_list_widget)
        self.comp_list_group.setLayout(comp_list_layout)

        # --- File List Group ---
        self.file_list_group = QGroupBox("Image Progress")
        file_list_layout = QVBoxLayout()
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemClicked.connect(self.file_selected)
        file_list_layout.addWidget(self.file_list_widget)
        self.file_list_group.setLayout(file_list_layout)

        self.splitter.addWidget(self.details_group)
        self.splitter.addWidget(self.comp_list_group)
        self.splitter.addWidget(self.file_list_group)
        self.splitter.setSizes([250, 400, 250])
        main_layout.addWidget(self.splitter)

    def _set_details_enabled(self, enabled: bool):
        self.name_edit.setEnabled(enabled)
        self.inputs_edit.setEnabled(enabled)
        self.outputs_edit.setEnabled(enabled)
        self.inouts_edit.setEnabled(enabled)

    def _on_name_changed(self):
        old_name = self._current_comp_name
        new_name = self.name_edit.text().strip()
        if old_name and new_name and old_name != new_name:
            self.component_name_changed.emit(old_name, new_name)
    
    def _on_connections_changed(self, conn_type: str):
        if not self._current_comp_name: return
        editor = {'input': self.inputs_edit, 'output': self.outputs_edit, 'inout': self.inouts_edit}[conn_type]
        self.component_connections_changed.emit(self._current_comp_name, conn_type, editor.text())

    def show_comp_context_menu(self, pos: QPoint):
        item = self.comp_list_widget.itemAt(pos)
        if not item: return

        context_menu = QMenu(self)
        delete_action = context_menu.addAction("Delete Component")
        action = context_menu.exec(self.comp_list_widget.mapToGlobal(pos))
        
        if action == delete_action:
            self.component_delete_requested.emit(item.text())

    def on_comp_selected(self, item):
        self.component_selected.emit(item.text())

    def update_component_list(self, component_names):
        self.comp_list_widget.clear()
        self.comp_list_widget.addItems(sorted(component_names))
    
    def update_file_list(self, file_names):
        self.file_list_widget.clear()
        self.file_list_widget.addItems(sorted(file_names, key=natural_sort_key))

    def update_details(self, component_name, details):
        if not details or not component_name:
            self._current_comp_name = None
            self.name_edit.clear()
            self.inputs_edit.clear()
            self.outputs_edit.clear()
            self.inouts_edit.clear()
            self._set_details_enabled(False)
            return

        self._set_details_enabled(True)
        self._current_comp_name = component_name
        
        # Block signals to prevent feedback loops while populating
        self.name_edit.blockSignals(True)
        self.inputs_edit.blockSignals(True)
        self.outputs_edit.blockSignals(True)
        self.inouts_edit.blockSignals(True)

        self.name_edit.setText(component_name)
        
        conns = details.get('connections', {})
        def format_conns(conn_list):
            items = []
            for c in conn_list:
                if c.get('count', 1) > 1:
                    items.append(f"{c['name']}*{c['count']}")
                else:
                    items.append(c['name'])
            return ", ".join(items)

        self.inputs_edit.setText(format_conns(conns.get('input', [])))
        self.outputs_edit.setText(format_conns(conns.get('output', [])))
        self.inouts_edit.setText(format_conns(conns.get('inout', [])))
        
        # Unblock signals
        self.name_edit.blockSignals(False)
        self.inputs_edit.blockSignals(False)
        self.outputs_edit.blockSignals(False)
        self.inouts_edit.blockSignals(False)
        
    def set_current_file_item(self, index):
        if 0 <= index < self.file_list_widget.count():
            self.file_list_widget.setCurrentRow(index)

    def get_current_file_index(self):
        return self.file_list_widget.currentRow()

    def get_file_count(self):
        return self.file_list_widget.count()