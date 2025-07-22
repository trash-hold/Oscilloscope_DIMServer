import sys
import json
import time
import threading
import numpy as np
import zmq


from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QTextEdit
)
from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QFont

from drivers.TDS3054C import TDS3054C
from manager.measurement_manager import MeasurementManager
from server.zmq_manager import *


class OscilloscopeControlGUI(QMainWindow):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Oscilloscope Synchronized Server")
        self.setGeometry(100, 100, 700, 450)

        with open(config_path, 'r') as f:
            config = json.load(f)

        # UI Widget Setup
        self.status_label = QLabel("Initializing...")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.start_button = QPushButton("Start Continuous Measurement")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_view)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Instantiate the Application Stack
        driver = TDS3054C(config['scope_ip'], config['scope_port'])
        manager = MeasurementManager(driver)
        self.server_manager = ServerManager(config, manager)

        # Connect Signals to GUI Slots
        self.server_manager.status_update.connect(self.update_status)
        self.start_button.clicked.connect(self.on_start_clicked)
        self.stop_button.clicked.connect(self.on_stop_clicked)
        
    @Slot(str)
    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")
        self.log_view.append(f"[{time.strftime('%H:%M:%S')}] {message}")

    @Slot()
    def on_start_clicked(self):
        self.server_manager.start_continuous_cycles()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    @Slot()
    def on_stop_clicked(self):
        self.server_manager.stop_continuous_cycles()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        self.server_manager.close()
        event.accept()