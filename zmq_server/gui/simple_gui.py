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
from drivers.TDS3054C import TDS3054C
from manager.measurement_manager import MeasurementManager
from server.zmq_manager import *
from common.exepction import * 
from gui.panels import ControlPanel


class OscilloscopeControlGUI(QMainWindow):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Oscilloscope Synchronized Server")
        self.setGeometry(100, 100, 1000, 500)

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to load or parse config file '{config_path}'.\n{e}")
            sys.exit(1)

        # Timeout configuration
        self.timeout_label = QLabel("Acquisition Timeout (s):")
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(1, 3600) # 1 second to 1 hour
        self.timeout_spinbox.setValue(10)      # Default to 10 seconds
        self.continue_on_timeout_checkbox = QCheckBox("Continue measurement on timeout")
        self.continue_on_timeout_checkbox.setChecked(False)

        # UI Widget Setup
        self.status_label = QLabel("Initializing...")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.start_button = QPushButton("Start Continuous Measurement")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)

        # Panels
        self.control_panel = ControlPanel()

        # Layout
        main_layout = QHBoxLayout()
        
        # Left side: Control Panel
        main_layout.addWidget(self.control_panel, 1) # Weight 1

        # Right side: Logging and operation controls
        right_v_layout = QVBoxLayout()
        right_v_layout.addWidget(self.status_label)
        right_v_layout.addWidget(self.log_view, 5) # Give log view more space

        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(self.timeout_label)
        timeout_layout.addWidget(self.timeout_spinbox)
        right_v_layout.addLayout(timeout_layout)
        right_v_layout.addWidget(self.continue_on_timeout_checkbox)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        right_v_layout.addLayout(button_layout)

        main_layout.addLayout(right_v_layout, 2) # Weight 2, takes more space

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
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

        self.control_panel.settings_changed.connect(self.on_settings_changed)
        self.control_panel._on_value_changed()

    
    @Slot(dict)
    def handle_error(self, error_data: dict):
        """
        Receives structured error data and presents an appropriate
        dialog box to the user based on the error type.
        """
        error_type = error_data.get('type', 'UnknownError')
        error_message = error_data.get('message', 'An unknown error occurred.')

        self.status_label.setText(f"Error: {error_message}")

        if error_type == "AcquisitionTimeoutError" and self.continue_on_timeout_checkbox.isChecked():
            self.log_message(f"WARNING ({error_type}): {error_message}. Continuing to next cycle.", "orange")
     
        elif error_type == "AcquisitionTimeoutError":
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

            self.set_ui_for_running_state(False)


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
        timeout = self.timeout_spinbox.value()
        continue_on_timeout = self.continue_on_timeout_checkbox.isChecked()
        self.server_manager.start_continuous_cycles(timeout, continue_on_timeout)
        
        self.set_ui_for_running_state(True) 

    @Slot()
    def on_stop_clicked(self):
        stop_message = "Stopping... The current cycle will be the last."
        self.status_label.setText(f"Status: {stop_message}")
        self.log_message(stop_message, "black") # Use default color
        
        self.server_manager.stop_continuous_cycles()
        self.set_ui_for_running_state(False)

    @Slot(dict)
    def on_settings_changed(self, settings: dict):
        """Forwards new measurement settings to the backend."""
        self.log_message("New settings received. Applying to next measurement.", "green")
        self.server_manager.update_measurement_config(settings)

    def set_ui_for_running_state(self, is_running: bool):
        """Disables/Enables UI controls based on the measurement state."""
        self.start_button.setEnabled(not is_running)
        self.stop_button.setEnabled(is_running)
        self.timeout_spinbox.setEnabled(not is_running)
        self.continue_on_timeout_checkbox.setEnabled(not is_running)
        self.control_panel.set_enabled_controls(not is_running)

    def closeEvent(self, event):
        self.server_manager.close()
        event.accept()