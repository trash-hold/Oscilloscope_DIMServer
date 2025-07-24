import json

from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer   # Integration with GUI
from common.exepction import *

from manager.measurement_manager import MeasurementManager 
from server.zmq_manager import ServerManager
from drivers.TDS3054C import TDS3054C


class BackendService(QObject):
    status_update = Signal(str)
    error_occurred = Signal(dict)

    AVAILABLE_DRIVERS = {
        "TDS3054C": TDS3054C,
    }

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        
        try:
            with open(config['device_profile_path'], 'r') as f:
                self.device_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ConfigurationError(f"Failed to load device profile '{config['device_profile_path']}'.\n{e}")

        # Get driver name and params from the device profile
        device_name = self.device_config.get("device_name")
        connection_params = self.device_config.get("connection_params")
        
        driver_class = self.AVAILABLE_DRIVERS.get(device_name)
        if not driver_class:
            raise ConfigurationError(f"Driver '{device_name}' not found or not supported.")
        if not connection_params:
            raise ConfigurationError(f"Connection parameters not found in profile for '{device_name}'.")
        
        # Instantiate driver with the connection_params dictionary
        driver = driver_class(connection_params)
        manager = MeasurementManager(driver)
        self.server_manager = ServerManager(config, manager)

        self.server_manager.status_update.connect(self.status_update)
        self.server_manager.error_occurred.connect(self.error_occurred)

    @Slot(dict)
    def update_measurement_config(self, settings: dict):
        self.server_manager.update_measurement_config(settings)

    @Slot(int, bool)
    def start_continuous_cycles(self, timeout: int, continue_on_timeout: bool):
        self.server_manager.start_continuous_cycles(timeout, continue_on_timeout)

    @Slot()
    def stop_continuous_cycles(self):
        self.server_manager.stop_continuous_cycles()

    def close(self):
        self.server_manager.close()