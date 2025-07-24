# Overall functionality
import sys
import json
import time

# GUI
from PySide6.QtWidgets import ( QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QTextEdit, QMessageBox, QSpinBox, QCheckBox, QHBoxLayout
)
from PySide6.QtCore import Slot

# Custom classes
from server.zmq_manager import *
from common.exepction import * 
from gui.panels import ControlPanel, ActionPanel
from server.backend import BackendService



class OscilloscopeControlGUI(QMainWindow):
    measurement_state_changed = Signal(bool) # True if running, False if stopped

    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Oscilloscope Control Framework")
        self.setGeometry(100, 100, 1000, 700)

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to load config file '{config_path}'.\n{e}")
            sys.exit(1)

        try:
            self.backend = BackendService(config)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize the backend.\n{e}")
            sys.exit(1)

#        self.create_layout()

    
    def create_layout(self) -> None:
        # Custom panels
        self.control_panel = ControlPanel(self.backend.device_config)
        self.action_panel = ActionPanel()

        # Layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.control_panel, 1)
        main_layout.addWidget(self.action_panel, 2)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Signals
        self.backend.status_update.connect(self.action_panel.update_status)
        self.backend.error_occurred.connect(self.handle_error)
        self.action_panel.start_button.clicked.connect(self.on_start_clicked)
        self.action_panel.stop_button.clicked.connect(self.on_stop_clicked)
        self.control_panel.settings_changed.connect(self.on_settings_changed)

        self.measurement_state_changed.connect(self.control_panel.set_enabled_controls)
        self.measurement_state_changed.connect(self.action_panel.set_running_state)

    
    @Slot(dict)
    def handle_error(self, error_data: dict):
        """
        Receives structured error data and presents an appropriate
        dialog box to the user based on the error type.
        """
        error_type = error_data.get('type', 'UnknownError')
        error_message = error_data.get('message', 'An unknown error occurred.')

        self.action_panel.status_label.setText(f"Error: {error_message}")

        if error_type == "AcquisitionTimeoutError" and self.continue_on_timeout_checkbox.isChecked():
            self.action_panel.log_message(f"WARNING ({error_type}): {error_message}. Continuing to next cycle.", "orange")
     
        elif error_type == "AcquisitionTimeoutError":
            QMessageBox.warning(self, "Acquisition Timeout", error_message)
            self.action_panel.log_message(f"WARNING ({error_type}): {error_message}", "orange") 
        
        elif error_type in ["DeviceConnectionError", "ConfigurationError", "UnexpectedDeviceError"]:
            # These are critical, likely unrecoverable hardware/config errors.
            QMessageBox.critical(self, "Hardware/Configuration Error", f"{error_message}\nPlease check the device connection and configuration, then restart the application.")
            self.action_panel.log_message(f"FATAL ({error_type}): {error_message}", "red")
            self.set_ui_for_running_state(False)
            self.start_button.setEnabled(False)

        else: # Catches ZMQ errors, UnhandledWorkerException, etc.
            QMessageBox.critical(self, "System Error", f"{error_message}\nThe measurement has been stopped. Check logs for details.")
            self.action_panel.log_message(f"CRITICAL ({error_type}): {error_message}", "purple")

            self.set_ui_for_running_state(False)

    @Slot()
    def on_start_clicked(self):
        timeout = self.action_panel.timeout_spinbox.value()
        continue_on_timeout = self.action_panel.continue_on_timeout_checkbox.isChecked()
        self.backend.start_continuous_cycles(timeout, continue_on_timeout)
        self.measurement_state_changed.emit(True)

    @Slot()
    def on_stop_clicked(self):
        stop_message = "Stopping... The current cycle will be the last."
        self.action_panel.update_status(stop_message)
        
        self.backend.stop_continuous_cycles()
        self.measurement_state_changed.emit(False)

    @Slot(dict)
    def on_settings_changed(self, settings: dict):
        """Forwards new measurement settings to the backend."""
        self.action_panel.log_message("New settings received. Applying to next measurement.", "green")
        
        self.backend.update_measurement_config(settings)

        
    def closeEvent(self, event):
        self.backend.close()
        event.accept()