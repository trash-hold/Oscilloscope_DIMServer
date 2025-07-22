import sys
import json
import time
import threading
import numpy as np
import zmq


from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QTextEdit, QMessageBox
)
from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QFont

from drivers.TDS3054C import TDS3054C
from manager.measurement_manager import MeasurementManager
from server.zmq_manager import *
from common.exepction import * 


class OscilloscopeControlGUI(QMainWindow):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Oscilloscope Synchronized Server")
        self.setGeometry(100, 100, 700, 450)

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to load or parse config file '{config_path}'.\n{e}")
            sys.exit(1)

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
        try:
            driver = TDS3054C(config['scope_ip'], config['scope_port'])
            manager = MeasurementManager(driver)
            self.server_manager = ServerManager(config, manager)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize the application stack.\n{e}")
            sys.exit(1)

        # Connect Signals to GUI Slots
        self.server_manager.status_update.connect(self.update_status)
        self.server_manager.error_occurred.connect(self.handle_error)
        self.start_button.clicked.connect(self.on_start_clicked)
        self.stop_button.clicked.connect(self.on_stop_clicked)

    
    @Slot(dict)
    def handle_error(self, error_data: dict):
        """
        Receives structured error data and presents an appropriate
        dialog box to the user based on the error type.
        """
        error_type = error_data.get('type', 'UnknownError')
        error_message = error_data.get('message', 'An unknown error occurred.')

        self.status_label.setText(f"Error: {error_message}")

        if error_type == "AcquisitionTimeoutError":
            QMessageBox.warning(self, "Acquisition Timeout", error_message)
            self.log_message(f"WARNING ({error_type}): {error_message}", "orange")
        
        elif error_type in ["DeviceConnectionError", "ConfigurationError", "UnexpectedDeviceError"]:
            # These are critical, likely unrecoverable hardware/config errors.
            QMessageBox.critical(self, "Hardware/Configuration Error", f"{error_message}\nPlease check the device connection and configuration, then restart the application.")
            self.log_message(f"FATAL ({error_type}): {error_message}", "red")
            self.set_ui_for_running_state(False)
            self.start_button.setEnabled(False)

        else: # Catches ZMQ errors, UnhandledWorkerException, etc.
            QMessageBox.critical(self, "System Error", f"{error_message}\nThe measurement has been stopped. Check logs for details.")
            self.log_message(f"CRITICAL ({error_type}): {error_message}", "purple")


    def log_message(self, message: str, color: str = "black"):
        """Appends a message to the log view with a specified color."""
        timestamp = time.strftime('%H:%M:%S')
        # Use HTML to set the color of the message text
        colored_message = f'<font color="{color}">[{timestamp}] {message}</font>'
        self.log_view.append(colored_message)

    @Slot(str)
    def update_status(self, message):
        """Handles normal status updates."""
        self.status_label.setText(f"Status: {message}")
        ## MODIFIED: Use the new logging helper.
        self.log_message(message, "blue")

    @Slot()
    def on_start_clicked(self):
        self.server_manager.start_continuous_cycles()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    @Slot()
    def on_stop_clicked(self):
        stop_message = "Stopping... The current cycle will be the last."
        self.status_label.setText(f"Status: {stop_message}")
        self.log_message(stop_message, "black") # Use default color
        
        self.server_manager.stop_continuous_cycles()
        self.set_ui_for_running_state(False)

    def closeEvent(self, event):
        self.server_manager.close()
        event.accept()