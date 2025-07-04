# src/widgets/right_panel.py
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QGroupBox, 
                             QLabel, QSplitter, QListWidgetItem, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

def natural_sort_key(s):
    """A key for natural sorting (e.g. 'item 1', 'item 2', 'item 10')."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', s)]

class RightPanel(QWidget):
    component_selected = pyqtSignal(str)
    component_delete_requested = pyqtSignal(str)
    file_selected = pyqtSignal(QListWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.details_group = QGroupBox("Component Details")
        details_layout = QVBoxLayout()
        self.details_label = QLabel("Select a component to see details.")
        self.details_label.setWordWrap(True)
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        details_layout.addWidget(self.details_label)
        self.details_group.setLayout(details_layout)

        self.comp_list_group = QGroupBox("Annotated Components")
        comp_list_layout = QVBoxLayout()
        self.comp_list_widget = QListWidget()
        self.comp_list_widget.itemClicked.connect(self.on_comp_selected)
        self.comp_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.comp_list_widget.customContextMenuRequested.connect(self.show_comp_context_menu)
        comp_list_layout.addWidget(self.comp_list_widget)
        self.comp_list_group.setLayout(comp_list_layout)

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
        # Use natural sorting for file names
        self.file_list_widget.addItems(sorted(file_names, key=natural_sort_key))

    def update_details(self, component_name, details):
        if not details:
            self.details_label.setText("Select a component to see details.")
            return

        conns = details.get('connections', {})
        inputs = ", ".join([c['name'] for c in conns.get('input', [])]) or "None"
        outputs = ", ".join([c['name'] for c in conns.get('output', [])]) or "None"
        inouts = ", ".join([c['name'] for c in conns.get('inout', [])]) or "None"

        text = f"""
        <b style='color:#c678dd;'>Name:</b> {component_name}<br>
        <b style='color:#e5c07b;'>Type:</b> {details.get('type', 'N/A')}<br>
        <hr>
        <b style='color:#98c379;'>Inputs:</b><br>{inputs}<br>
        <b style='color:#e06c75;'>Outputs:</b><br>{outputs}<br>
        <b style='color:#61afef;'>In/Outs:</b><br>{inouts}
        """
        self.details_label.setText(text)
        
    def set_current_file_item(self, index):
        if 0 <= index < self.file_list_widget.count():
            self.file_list_widget.setCurrentRow(index)

    def get_current_file_index(self):
        return self.file_list_widget.currentRow()

    def get_file_count(self):
        return self.file_list_widget.count()