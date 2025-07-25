import logging 

from server.backend import BackendWorker 


def main():
    """Main entry point for the headless backend server."""
    logging.info("--- Starting Oscilloscope Backend Server ---")
    
    config = {
        "dim_server_endpoint": "tcp://localhost:5555",
        "local_command_endpoint": "tcp://*:5556",
        "local_publish_endpoint": "tcp://*:5557",
    }

    try:
        # --- Initialize Hardware ---
        # This is where you would configure your actual hardware connection
        # For demonstration, we assume a mock or real driver class.
        # connection_params = {"ip_address": "192.168.1.100"}
        # driver = TDS3054C(connection_params)
        # manager = MeasurementManager(driver)
        
        # Using a mock manager for standalone testing:
        class MockManager:
            def query(self, q): return f"Mock reply to '{q}'"
            def write(self, c): logging.info(f"Mock write: {c}")
            def apply_settings(self, s): logging.info(f"Mock applying settings: {s}")
            def sample(self, timeout): import numpy as np; return np.sin(np.linspace(0, 10, 1000) + time.time())
        
        manager = MockManager()
        
        # --- Initialize and Run Worker ---
        worker = BackendWorker(manager, config)
        worker.run()

    except Exception as e:
        logging.critical(f"Failed to initialize and run the backend: {e}", exc_info=True)

if __name__ == "__main__":
    main()