

from drivers.TDS3054C import TDS3054C
from drivers.AbstractInterfaces import Oscilloscope
from common.exepction import ConfigurationError

from enum import Enum

# This dictionary maps a string name to the driver class
DRIVER_MAP = {
    "TDS3054C": TDS3054C,
    # "AnotherScope": AnotherScope,
}

def create_driver(driver_name: str, connection_params: dict) -> Oscilloscope:
    """
    Factory function to create a driver instance from its name.
    
    Args:
        driver_name: The name of the driver to instantiate (e.g., "TDS3054C").
        connection_params: A dictionary with connection details (e.g., ip, port).

    Returns:
        An instance of a class that inherits from Oscilloscope.
        
    Raises:
        ConfigurationError: If the driver name is not found.
    """
    driver_class = DRIVER_MAP.get(driver_name)
    
    if not driver_class:
        raise ConfigurationError(f"Driver '{driver_name}' not found in DRIVER_MAP.")
        
    print(f"Creating instance of driver: {driver_name}")
    return driver_class(connection_params)



class Command(Enum):
    """
    Defines the command contract between the C++ server and the Python backend.
    
    The member name (e.g., SET_TRIGGER_SLOPE) is used internally in Python.
    The member value (e.g., "set_trigger_slope") is the string sent over ZMQ.
    """
    # Commands originating from the DIM server
    SET_CHANNEL_ENABLED = "set_channel_enabled"
    SET_CHANNEL_SCALE = "set_channel_scale"
    SET_TRIGGER_CHANNEL = "set_trigger_channel"
    SET_TRIGGER_SLOPE = "set_trigger_slope"
    SET_TRIGGER_LEVEL = "set_trigger_level"
    SET_ACQUISITION_MODE = "set_acquisition_mode"
    SET_ACQUISITION_TIMEDIV = "set_acquisition_timediv"
    SET_ACQUISITION_TIMEOUT = "set_acquisition_timeout"
    SET_ACQUISITION_IGNORE = "set_acquisition_ignore"
    RAW_QUERY = "raw_query"
    RAW_WRITE = "raw_write"

class AcquistionMode(Enum):
    CONTINUOUS = "CONT"
    SINGLE = "SINGLE"
    OFF = "OFF"