from gui.simple_gui import OscilloscopeControlGUI
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QTextEdit
)
from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QFont
import json
import sys

CONFIG_FILE = "../secret/config.json"


if __name__ == '__main__':

    config = None
    with open(CONFIG_FILE, 'r') as file:
        config = json.load(file)
        file.close()

    # 2. Run the application
    app = QApplication(sys.argv)
    window = OscilloscopeControlGUI(config_path=CONFIG_FILE)
    window.show()
    sys.exit(app.exec())