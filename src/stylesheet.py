# src/stylesheet.py

STYLE_SHEET = """
QWidget {
    /* Use a more cross-platform friendly font stack and larger base font size */
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 12pt;
}

QMainWindow {
    background-color: #282c34;
}

QSplitter::handle {
    background-color: #3a3f4b;
    border: 1px solid #282c34;
}
QSplitter::handle:hover {
    background-color: #4f5563;
}
QSplitter::handle:pressed {
    background-color: #586999;
}

QGroupBox {
    color: #abb2bf;
    font-weight: bold;
    border: 1px solid #3a3f4b;
    border-radius: 8px;
    margin-top: 1ex;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 2px 8px;
    background-color: #3a3f4b;
    border-radius: 4px;
}

QPushButton {
    background-color: #5c6bc0;
    color: white;
    border: none;
    padding: 10px;
    border-radius: 5px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #7986cb;
}
QPushButton:pressed {
    background-color: #3f51b5;
}
QPushButton:disabled {
    background-color: #4a4f5a;
    color: #9da5b4;
}

QListWidget {
    background-color: #21252b;
    color: #abb2bf;
    border: 1px solid #3a3f4b;
    border-radius: 5px;
    padding: 5px;
}
QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background-color: #3a3f4b;
}
QListWidget::item:selected {
    background-color: #5c6bc0;
    color: white;
}

/* Style for the new editable fields in RightPanel */
QLabel {
    color: #abb2bf;
    padding-top: 6px;
}

QFormLayout QLabel { /* Specifically target labels in form layouts */
    padding-top: 8px;
}

QDialog {
    background-color: #282c34;
}

QLineEdit, QComboBox {
    background-color: #21252b;
    color: #abb2bf;
    border: 1px solid #3a3f4b;
    border-radius: 4px;
    padding: 6px;
    min-height: 20px; /* Ensure a decent height */
}
QLineEdit:focus, QComboBox:focus {
    border-color: #5c6bc0;
}
QLineEdit:disabled {
    background-color: #2c313a;
    color: #6a7181;
}

QComboBox::drop-down {
    border: none;
}
QComboBox::down-arrow {
    image: url(noop); /* Hide default arrow if needed, or style it */
}


QMessageBox {
    background-color: #282c34;
}
QMessageBox QLabel {
    color: #abb2bf;
}
"""