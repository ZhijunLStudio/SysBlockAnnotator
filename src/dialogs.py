# src/dialogs.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QDialogButtonBox

class ComponentNameDialog(QDialog):
    """一个简单的对话框，用于获取组件名称"""
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
        """获取输入的名称"""
        if self.exec() == QDialog.DialogCode.Accepted:
            return self.name_input.text().strip()
        return None