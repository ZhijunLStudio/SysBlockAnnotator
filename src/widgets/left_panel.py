# src/widgets/left_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QGroupBox, QFileDialog
from PyQt6.QtCore import pyqtSignal

class LeftPanel(QWidget):
    load_images_requested = pyqtSignal(str)
    load_jsons_requested = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    save_requested = pyqtSignal()
    prev_image_requested = pyqtSignal()
    next_image_requested = pyqtSignal()
    toggle_connections_view_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)

        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout()
        self.btn_load_images = QPushButton("Load Image Folder")
        self.btn_load_jsons = QPushButton("Load JSON Folder")
        self.btn_save = QPushButton("Save Current (Ctrl+S)")
        self.btn_load_images.clicked.connect(self.on_load_images)
        self.btn_load_jsons.clicked.connect(self.on_load_jsons)
        self.btn_save.clicked.connect(self.save_requested)
        self.btn_save.setShortcut("Ctrl+S")
        data_layout.addWidget(self.btn_load_images)
        data_layout.addWidget(self.btn_load_jsons)
        data_layout.addWidget(self.btn_save)
        data_group.setLayout(data_layout)

        nav_group = QGroupBox("Navigation")
        nav_layout = QVBoxLayout()
        self.btn_prev = QPushButton("Previous Image (A)")
        self.btn_next = QPushButton("Next Image (D)")
        self.btn_prev.clicked.connect(self.prev_image_requested)
        self.btn_next.clicked.connect(self.next_image_requested)
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.btn_next)
        nav_group.setLayout(nav_layout)
        
        anno_group = QGroupBox("Annotation Tools")
        anno_layout = QVBoxLayout()
        self.btn_draw_box = QPushButton("Annotate Component (W)")
        
        # --- NEW SIMPLIFIED BUTTONS ---
        self.btn_connect_uni = QPushButton("Unidirectional Arrow (O)")
        self.btn_connect_bi = QPushButton("Bidirectional Arrow (N)")
        
        self.btn_toggle_connections = QPushButton("Toggle View (V)")
        
        self.btn_toggle_connections.clicked.connect(self.toggle_connections_view_requested)
        
        self.btn_draw_box.setShortcut("W")
        self.btn_connect_uni.setShortcut("O")
        self.btn_connect_bi.setShortcut("N")

        self.btn_draw_box.clicked.connect(lambda: self.mode_changed.emit('drawing_box'))
        self.btn_connect_uni.clicked.connect(lambda: self.mode_changed.emit('connect_unidirectional'))
        self.btn_connect_bi.clicked.connect(lambda: self.mode_changed.emit('connect_bidirectional'))

        anno_layout.addWidget(self.btn_draw_box)
        anno_layout.addWidget(self.btn_connect_uni)
        anno_layout.addWidget(self.btn_connect_bi)
        anno_layout.addWidget(self.btn_toggle_connections)
        anno_group.setLayout(anno_layout)

        self.layout.addWidget(data_group)
        self.layout.addWidget(nav_group)
        self.layout.addWidget(anno_group)
        self.layout.addStretch()

    def update_toggle_button_text(self, show_all: bool):
        if show_all:
            self.btn_toggle_connections.setText("Show Selected Only (V)")
        else:
            self.btn_toggle_connections.setText("Show All Connections (V)")

    def on_load_images(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder_path: self.load_images_requested.emit(folder_path)

    def on_load_jsons(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select JSON Folder")
        if folder_path: self.load_jsons_requested.emit(folder_path)