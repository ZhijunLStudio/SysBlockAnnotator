# src/dialogs.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QDialogButtonBox, QComboBox, QLabel

class ComponentNameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Component Name")
        self.layout = QVBoxLayout(self)
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Component Name")
        self.layout.addWidget(self.name_input)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_name(self):
        if self.exec() == QDialog.DialogCode.Accepted:
            return self.name_input.text().strip()
        return None

class SkipReasonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Skip Image")
        self.layout = QVBoxLayout(self)
        
        self.label = QLabel("Please provide a reason for skipping this image:")
        self.layout.addWidget(self.label)
        
        self.reason_combo = QComboBox()
        self.reasons = [
            "Contains basic elements", 
            "Parent/child diagram", 
            "Series/parallel connection"
        ]
        self.reason_combo.addItems([""] + self.reasons) # Add a blank first item
        self.layout.addWidget(self.reason_combo)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        
        # Disable OK until a reason is selected
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)
        self.reason_combo.currentIndexChanged.connect(self.check_selection)

    def check_selection(self, index):
        self.ok_button.setEnabled(index > 0)

    def get_reason(self):
        if self.exec() == QDialog.DialogCode.Accepted:
            return self.reason_combo.currentText()
        return None