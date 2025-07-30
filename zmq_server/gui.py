from gui.dashboard import OscilloscopeMonitorGUI
from PySide6.QtWidgets import (
    QApplication
)
import json
import sys

CONFIG_FILE = "../secret/config.json"


if __name__ == '__main__':

    app = QApplication(sys.argv)
    window = OscilloscopeMonitorGUI(config_path=CONFIG_FILE)
    window.show()
    sys.exit(app.exec())