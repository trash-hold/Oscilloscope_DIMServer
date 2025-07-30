import json
import logging
import os
import sys
from manager.measurement_manager import MeasurementManager
from server.backend import BackendWorker
from common.utils import create_driver
from common.exepction import *


def main():
    """
    Initializes and runs the backend application.
    This script is the "Assembler" that builds the application from its components.
    """

    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # Set the lowest level to capture everything

    # Create a handler to print logs to the console (for headless mode)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    logging.info("Console logger initialized. Starting backend setup...")
    
    try:
        # 1. Load Main Application Configuration
        app_config_path = '../secret/config.json'
        logging.info(f"Loading application configuration from {app_config_path}...")
        with open(app_config_path, 'r') as f:
            app_config = json.load(f)

        # 2. Load the Hardware-Specific Device Profile
        profile_path = app_config.get('device_profile_path')
        if not profile_path:
            raise ConfigurationError("'device_profile_path' not found in app_config.json")
        
        logging.info(f"Loading device profile from {profile_path}...")
        with open(profile_path, 'r') as f:
            device_profile = json.load(f)

        # 3. Create the specific driver instance using the factory
        driver_name = device_profile.get('driver_name')
        connection_params = device_profile.get('connection_params')
        if not driver_name or not connection_params:
            raise ConfigurationError("Profile must contain 'driver_name' and 'connection_params'.")

        driver = create_driver(driver_name, connection_params)
        
        # 4. Test the connection to the physical device
        logging.info(f"Testing connection to {driver_name}...")
        driver.test_connection()
        logging.info("Device connection successful.")

        # 5. Create the MeasurementManager, injecting ONLY the driver.
        # The manager is now properly abstracted from any config files.
        measurement_manager = MeasurementManager(dev=driver)

        # 6. Create the BackendWorker, injecting all its dependencies.
        # It gets the manager for actions, the app_config for ZMQ, and the
        # device_profile to serve to clients.
        worker = BackendWorker(
            manager=measurement_manager,
            config=app_config,
            device_profile=device_profile
        )
        
        logging.info("Starting backend worker...")
        worker.run()

    except FileNotFoundError as e:
        logging.critical(f"FATAL: A required configuration file was not found. {e}")
    except (ConfigurationError, DeviceConnectionError, DeviceError) as e:
        logging.critical(f"FATAL: An error occurred during setup. {e}")
    except Exception as e:
        logging.critical(f"An unexpected fatal error occurred in the main thread: {e}", exc_info=True)

if __name__ == '__main__':
    main()