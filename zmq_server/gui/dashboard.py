import sys
import json
import logging

# GUI
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox, QSplitter
from PySide6.QtCore import Slot, Signal, Qt

# Backend
from server.gui_backend import ServerManager 

# Custom UI panels
from gui.panels import LogPanel, PlotPanel

# Error handling
from common.exepction import * 

class OscilloscopeMonitorGUI(QMainWindow):

    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Oscilloscope Monitor")
        self.setGeometry(100, 100, 1200, 800)
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to load config file '{config_path}'.\n{e}")
            sys.exit(1)

        try:
            self.backend_communicator = ServerManager(self.config)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize ZMQ.\n{e}")
            sys.exit(1)

        self.create_layout()
        self.connect_signals()

    def create_layout(self) -> None:
        """Creates the main window layout with our new LogPanel."""
        self.log_panel = LogPanel()
        self.plot_panel = PlotPanel()

        splitter = QSplitter(Qt.Horizontal) # Arrange panels side-by-side
        splitter.addWidget(self.plot_panel)
        splitter.addWidget(self.log_panel)

        splitter.setSizes([800, 400])

        self.setCentralWidget(splitter)

    def connect_signals(self) -> None:
        """Connects signals from the backend communicator to the LogPanel."""
        self.backend_communicator.log_update.connect(self.log_panel.log_message)
        self.backend_communicator.backend_state_update.connect(self.log_panel.update_status)
        self.backend_communicator.error_occurred.connect(self.handle_error)
        self.backend_communicator.waveform_update.connect(self.plot_panel.update_waveforms)

    @Slot(str)
    def handle_error(self, error_message: str):
        """Shows a popup for critical errors received on the 'error' topic."""
        self.log_panel.log_message(f"CRITICAL: {error_message}")
        QMessageBox.warning(self, "Backend Error", error_message)

    @Slot(dict)
    def on_waveform_update(self, waveform_data: dict):
        """Placeholder for future plot panel."""
        self.log_panel.log_message("Received waveform data.", "green")

    def closeEvent(self, event):
        """Ensures the communicator thread is shut down cleanly."""
        self.backend_communicator.close()
        event.accept()