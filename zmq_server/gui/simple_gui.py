import sys
import json

# GUI
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox
from PySide6.QtCore import Slot, Signal

# Backend
from server.zmq_manager import ServerManager 

# Custom UI panels
from gui.panels import ControlPanel, ActionPanel

# Error handling
from common.exepction import * 

class OscilloscopeControlGUI(QMainWindow):

    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Oscilloscope Control GUI (State-Driven)")
        self.setGeometry(100, 100, 1000, 700)

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to load config file '{config_path}'.\n{e}")
            sys.exit(1)

        try:
            self.backend_communicator = ServerManager(self.config)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize the ZMQ communicator.\n{e}\n\nIs the backend process running?")
            sys.exit(1)

        self.create_layout()
        self.connect_signals()

        self.on_backend_state_update("IDLE")

    def create_layout(self) -> None:
        """Creates the main window layout using custom panels."""
        try:
            with open(self.config['device_profile_path'], 'r') as f:
                device_config = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Device Profile Error", f"Failed to load device profile.\n{e}")
            device_config = {} # Use an empty config to prevent crashing

        self.control_panel = ControlPanel(device_config)
        self.action_panel = ActionPanel()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.control_panel, 1)
        main_layout.addWidget(self.action_panel, 2)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def connect_signals(self) -> None:
        """Connects all signals and slots for the application."""
        # --- Connect to the new ServerManager's signals ---
        self.backend_communicator.backend_state_update.connect(self.on_backend_state_update)
        self.backend_communicator.status_update.connect(self.action_panel.update_status)
        self.backend_communicator.error_occurred.connect(self.handle_error)
        self.backend_communicator.waveform_update.connect(self.on_waveform_update)
        self.backend_communicator.reply_update.connect(self.on_command_reply)

        # Connect signals from UI elements to this window's slots
        self.action_panel.start_button.clicked.connect(self.on_start_clicked)
        self.action_panel.stop_button.clicked.connect(self.on_stop_clicked)
        self.control_panel.settings_changed.connect(self.on_settings_changed)


    @Slot(str)
    def handle_error(self, error_message: str):
        """
        Receives a simple error string from the backend and displays it.
        The backend is now responsible for formatting the error.
        """
        self.action_panel.log_message(f"ERROR: {error_message}", "red")
        QMessageBox.warning(self, "Backend Error", error_message)

    @Slot(str)
    def on_backend_state_update(self, state_name: str):
        """
        Drives the UI state based on messages from the backend.
        This is the single source of truth for the UI's state.
        """
        self.action_panel.update_status(f"Backend state: {state_name}")
        
        if state_name == "CONTINUOUS_ACQUISITION":
            self.control_panel.set_enabled_controls(False)
            self.action_panel.set_running_state(True)
        elif state_name == "IDLE":
            self.control_panel.set_enabled_controls(True)
            self.action_panel.set_running_state(False)
        elif state_name == "BUSY":
            self.control_panel.set_enabled_controls(False)
            self.action_panel.set_running_state(True) # Visually similar to running
            self.action_panel.start_button.setEnabled(False)
            self.action_panel.stop_button.setEnabled(False)
        else: # Handle other or unknown states
            self.control_panel.set_enabled_controls(False)
            self.action_panel.set_running_state(False)

    @Slot()
    def on_start_clicked(self):
        """
        Sends the 'start' command to the backend.
        The backend is responsible for its own settings (like timeout).
        """
        self.action_panel.log_message("Sending 'start' command...", "gray")
        self.backend_communicator.start_continuous()

    @Slot()
    def on_stop_clicked(self):
        """Sends the 'stop' command to the backend."""
        self.action_panel.log_message("Sending 'stop' command...", "gray")
        self.backend_communicator.stop_continuous()

    @Slot(dict)
    def on_settings_changed(self, settings: dict):
        """Forwards new measurement settings to the backend."""
        self.action_panel.log_message("New settings received. Sending to backend...", "green")
        self.backend_communicator.apply_settings(settings)

    @Slot(dict)
    def on_waveform_update(self, waveform_data: dict):
        """Placeholder slot to handle incoming waveform data."""
        # This is where you would update a plot widget
        points = waveform_data.get('points', 0)
        self.action_panel.log_message(f"Received waveform with {points} points.", "blue")

    @Slot(dict)
    def on_command_reply(self, reply: dict):
        """Handles generic replies from commands sent to the backend."""
        status = reply.get("status", "unknown")
        payload = reply.get("payload", "No payload.")
        if status == "ok":
            self.action_panel.log_message(f"Backend reply: {payload}", "gray")
        else:
            message = reply.get("message", "Unknown error.")
            self.action_panel.log_message(f"Backend command error: {message}", "orange")

    def closeEvent(self, event):
        """Ensures the communicator thread is shut down cleanly."""
        self.backend_communicator.close()
        event.accept()