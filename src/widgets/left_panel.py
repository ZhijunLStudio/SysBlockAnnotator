# src/widgets/left_panel.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QGroupBox, 
                             QFileDialog, QHBoxLayout, QLineEdit, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt

class LeftPanel(QWidget):
    load_images_requested = pyqtSignal(str)
    load_jsons_requested = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    save_requested = pyqtSignal()
    prev_image_requested = pyqtSignal()
    next_image_requested = pyqtSignal()
    skip_image_requested = pyqtSignal(str)
    toggle_connections_view_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)

        # --- Data Management Group ---
        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout()
        self.btn_load_images = QPushButton("Load Image Folder")
        self.btn_load_jsons = QPushButton("Load JSON Folder")
        self.btn_save = QPushButton("Save Current (Ctrl+S)")
        self.btn_load_images.clicked.connect(self.on_load_images)
        self.btn_load_jsons.clicked.connect(self.on_load_jsons)
        self.btn_save.clicked.connect(self.save_requested)
        # We keep this one because Ctrl+S is an Action, not a simple key press
        self.btn_save.setShortcut("Ctrl+S")
        data_layout.addWidget(self.btn_load_images)
        data_layout.addWidget(self.btn_load_jsons)
        data_layout.addWidget(self.btn_save)
        data_group.setLayout(data_layout)

        # --- Navigation Group ---
        nav_group = QGroupBox("Navigation")
        nav_layout = QVBoxLayout()
        self.btn_prev = QPushButton("Previous Image (A)")
        self.btn_next = QPushButton("Next Image (D)")
        self.btn_prev.clicked.connect(self.prev_image_requested)
        self.btn_next.clicked.connect(self.next_image_requested)
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.btn_next)
        nav_group.setLayout(nav_layout)
        
        # --- Annotation Tools Group ---
        anno_group = QGroupBox("Annotation Tools")
        anno_layout = QVBoxLayout()
        self.btn_draw_box = QPushButton("Annotate Component (W)")
        self.btn_connect_uni = QPushButton("Unidirectional Arrow (O)")
        self.btn_connect_bi = QPushButton("Bidirectional Arrow (N)")
        self.btn_toggle_connections = QPushButton("Toggle View (V)")
        
        # REMOVED .setShortcut() from here
        self.btn_toggle_connections.clicked.connect(self.toggle_connections_view_requested)
        self.btn_draw_box.clicked.connect(lambda: self.mode_changed.emit('drawing_box'))
        self.btn_connect_uni.clicked.connect(lambda: self.mode_changed.emit('connect_unidirectional'))
        self.btn_connect_bi.clicked.connect(lambda: self.mode_changed.emit('connect_bidirectional'))
        anno_layout.addWidget(self.btn_draw_box)
        anno_layout.addWidget(self.btn_connect_uni)
        anno_layout.addWidget(self.btn_connect_bi)
        anno_layout.addWidget(self.btn_toggle_connections)
        anno_group.setLayout(anno_layout)

        # --- Skip Image Group ---
        skip_group_container = QGroupBox("Skip Image")
        skip_main_layout = QVBoxLayout(skip_group_container)
        self.toggle_skip_button = QPushButton()
        self.toggle_skip_button.setCheckable(True)
        self.toggle_skip_button.setChecked(False)
        self.toggle_skip_button.setStyleSheet("text-align: left; padding-left: 10px;")
        self.toggle_skip_button.clicked.connect(self.toggle_skip_panel)
        skip_main_layout.addWidget(self.toggle_skip_button)
        self.skip_reasons_panel = QWidget()
        self.skip_layout = QVBoxLayout(self.skip_reasons_panel)
        self.skip_reasons_panel.setVisible(False)
        skip_main_layout.addWidget(self.skip_reasons_panel)
        add_reason_layout = QHBoxLayout()
        self.new_reason_input = QLineEdit()
        self.new_reason_input.setPlaceholderText("Add new reason...")
        self.btn_add_reason = QPushButton("+")
        self.btn_add_reason.setFixedSize(30, 30)
        self.btn_add_reason.clicked.connect(self.add_new_reason)
        add_reason_layout.addWidget(self.new_reason_input)
        add_reason_layout.addWidget(self.btn_add_reason)
        self.skip_layout.addLayout(add_reason_layout)
        self.skip_reasons = ["Contains basic elements", "Parent/child diagram", "Series/parallel connection"]
        self.reason_buttons_layout = QVBoxLayout()
        self.skip_layout.addLayout(self.reason_buttons_layout)
        self.update_reason_buttons()

        self.layout.addWidget(data_group)
        self.layout.addWidget(nav_group)
        self.layout.addWidget(anno_group)
        self.layout.addWidget(skip_group_container)
        self.layout.addStretch()
        self.toggle_skip_panel(False)

    def toggle_skip_panel(self, checked):
        self.skip_reasons_panel.setVisible(checked)
        if checked: self.toggle_skip_button.setText("[-] Hide Skip Reasons")
        else: self.toggle_skip_button.setText("[+] Show Skip Reasons")

    def update_reason_buttons(self):
        while self.reason_buttons_layout.count():
            child = self.reason_buttons_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        for reason in self.skip_reasons:
            btn = QPushButton(reason)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, r=reason: self.skip_image_requested.emit(r))
            self.reason_buttons_layout.addWidget(btn)

    def add_new_reason(self):
        new_reason = self.new_reason_input.text().strip()
        if new_reason and new_reason not in self.skip_reasons:
            self.skip_reasons.append(new_reason)
            self.update_reason_buttons()
            self.new_reason_input.clear()

    def update_toggle_button_text(self, show_all: bool):
        text = "Show Selected Only (V)" if show_all else "Show All Connections (V)"
        self.btn_toggle_connections.setText(text)

    def on_load_images(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Image Folder", options=QFileDialog.Option.DontUseNativeDialog)
        if folder_path: self.load_images_requested.emit(folder_path)

    def on_load_jsons(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select JSON Folder", options=QFileDialog.Option.DontUseNativeDialog)
        if folder_path: self.load_jsons_requested.emit(folder_path)