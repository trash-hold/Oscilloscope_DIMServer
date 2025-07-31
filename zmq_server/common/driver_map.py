from zmq_server.drivers.TDS3054C import TDS3054C
from zmq_server.drivers.AbstractInterfaces import Oscilloscope
from zmq_server.common.exceptions import ConfigurationError

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