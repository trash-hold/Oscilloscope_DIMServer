# backend.py

import json
import logging
from enum import Enum, auto
from manager.measurement_manager import MeasurementManager
from common.exepction import *
from server.zmq_manager import ZMQCommunicator
from common.utils import Command 

# This Enum defines the possible operational states of the worker.
class WorkerState(Enum):
    IDLE = auto()
    BUSY = auto()
    CONTINUOUS_ACQUISITION = auto()

class BackendWorker:
    """
    The core of the headless backend. Manages application state and delegates
    all communication to its ZMQCommunicator instance.
    """
    def __init__(self, manager: MeasurementManager, config: dict, device_profile: dict):
        self.manager = manager
        self.state = WorkerState.IDLE
        self.device_profile = device_profile
        
        # The worker owns a communicator instance to handle all ZMQ logic.
        self.comm = ZMQCommunicator(config)

        # This map connects command strings to the methods that handle them.
        self.COMMAND_MAP = {
            # DIM commands
            Command.SET_CHANNEL_ENABLED: self._handle_set_channel_state,
            Command.SET_CHANNEL_SCALE: self._handle_set_channel_volts,
            Command.SET_TRIGGER_SLOPE: self._handle_set_trigger_slope,
            Command.SET_TRIGGER_LEVEL: self._handle_set_trigger_level,
            Command.SET_ACQUISITION_STATE: self._handle_set_acq_state,
            Command.RAW_QUERY: self._handle_raw_query,
            Command.RAW_WRITE: self._handle_raw_write,

            # GUI/Local commands
            Command.APPLY_SETTINGS: self._handle_apply_settings,
            Command.START_CONTINUOUS_ACQUISITION: self._handle_start_continuous_acquisition,
            Command.STOP_CONTINUOUS_ACQUISITION: self._handle_stop_continuous_acquisition,
            Command.GET_DEVICE_PROFILE: self._handle_get_device_profile,
        }
        logging.info("BackendWorker initialized.")

    def run(self):
        """
        The main application loop. This version correctly handles requests
        by processing and replying immediately within the appropriate scope,
        which prevents the 'NameError'.
        """
        logging.info("Sending handshake to DIM server...")
        self.comm.reply_to_dim({"type": "handshake", "payload": "Python client online"})
        
        while True:
            try:
                # Set a non-blocking poll timeout when in continuous mode, otherwise wait.
                poll_timeout = 0 if self.state == WorkerState.CONTINUOUS_ACQUISITION else None
                sockets_with_data = self.comm.poll(poll_timeout)

                # --- Process incoming commands from the DIM Server ---
                # The code inside this 'if' block only runs when a message is received from DIM.
                if self.comm.dim_socket in sockets_with_data:
                    # Step 1: Receive a request from DIM. 'request' is defined here.
                    request = self.comm.receive_from_dim()
                    
                    # Step 2: Process it immediately to get a reply.
                    reply = self._dispatch_request(request)
                    
                    # Step 3: Send the reply back to DIM.
                    self.comm.reply_to_dim(reply)

                # --- Process incoming commands from the GUI ---
                # The code inside this 'if' block only runs when a message is received from the GUI.
                if self.comm.gui_socket in sockets_with_data:
                    # Step 1: Receive a request from the GUI. 'request' is defined here.
                    request = self.comm.receive_from_gui()
                    
                    # Step 2: Process it immediately to get a reply.
                    reply = self._dispatch_request(request)
                    
                    # Step 3: Send the reply back to the GUI.
                    self.comm.reply_to_gui(reply)

                # --- Handle Continuous Acquisition State ---
                # This runs only if no stop command was received in this loop iteration.
                if self.state == WorkerState.CONTINUOUS_ACQUISITION:
                    self._perform_one_acquisition_cycle()

            except KeyboardInterrupt:
                logging.info("Shutdown signal received. Exiting...")
                break
            except Exception as e:
                logging.critical(f"An unhandled exception occurred in the main loop: {e}", exc_info=True)
                self.set_state(WorkerState.IDLE)
                self.comm.publish_to_gui("error", f"Critical error: {e}. Returning to IDLE.")
        
        # Cleanly shut down all ZMQ resources before exiting.
        self.comm.stop()

    def _dispatch_request(self, request: dict) -> dict:
        """
        It converts the incoming command string into a PythonCommand member before looking it up in the map.
        """
        command_str = request.get("command")
        logging.debug(f"Dispatching request for command string '{command_str}' in state {self.state.name}")

        try:
            if not command_str:
                raise ValueError("Request dictionary is missing the 'command' field.")
            
            # --- Convert the incoming string to an Enum member ---
            command_enum = Command(command_str)
            
            params = request.get("params", {})

            if self.state == WorkerState.BUSY:
                raise PermissionError("Device is busy with a previous command.")

            # --- Look up the handler using the Enum member ---
            handler = self.COMMAND_MAP.get(command_enum)
            
            # This check is now almost redundant, as the Enum conversion
            # already validates the command, but it's good for safety.
            if not handler:
                raise NotImplementedError(f"Command '{command_enum.name}' is valid but has no handler.")

            result = handler(params)
            reply = {"status": "ok", "payload": result if result is not None else "Success"}

        except ValueError:
            # This block now catches invalid command strings from the Enum conversion.
            reply = {"status": "error", "message": f"Unknown command: '{command_str}'"}
        except PermissionError as e:
            reply = {"status": "error", "message": str(e)}
        except Exception as e:
            logging.critical(f"Error processing command '{command_str}': {e}", exc_info=True)
            reply = {"status": "error", "message": f"Internal Python error: {e}"}

        logging.debug(f"Returning reply for '{command_str}': {reply}")
        return reply

    def _handle_raw_query(self, params: dict) -> str:
        """Handles a raw query command by executing it through the manager."""
        query_string = params.get('query')
        if not query_string:
            raise ValueError("Parameter 'query' is required for raw_query.")
        # The manager's execute method is smart enough to handle queries
        return self._execute_blocking_task(self.manager.execute_raw_command, query_string)

    def _handle_raw_write(self, params: dict) -> str:
        """Handles a raw write command by executing it through the manager."""
        command_string = params.get('command')
        if not command_string:
            raise ValueError("Parameter 'command' is required for raw_write.")
        # The manager's execute method handles writes as well
        return self._execute_blocking_task(self.manager.execute_raw_command, command_string)
    
    def _execute_blocking_task(self, func, *args, **kwargs):
        """A safe wrapper for tasks that ensures state is managed correctly."""
        self.set_state(WorkerState.BUSY)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            self.set_state(WorkerState.IDLE)

    def set_state(self, new_state: WorkerState):
        """Changes state and publishes the update to the GUI."""
        if self.state == new_state: return
        self.state = new_state
        logging.info(f"STATE CHANGE: {self.state.name}")
        self.comm.publish_to_gui("backend_state", self.state.name)

    def _perform_one_acquisition_cycle(self):
        """Acquires data and publishes it using the communicator."""
        try:
            waveform_data = self.manager.sample(timeout=10)
            waveform_str = ",".join(map(str, waveform_data))
            self.comm.publish_to_dim("waveform", waveform_str)
            gui_payload = {"points": len(waveform_data), "data": waveform_data.tolist()}
            self.comm.publish_to_gui("waveform", gui_payload)
        except AcquisitionTimeoutError as e:
            self.comm.publish_to_gui("error", f"Acquisition Timeout: {e}")
        except Exception as e:
            self.comm.publish_to_gui("error", f"Error in acquisition cycle: {e}")
            self.set_state(WorkerState.IDLE)

    # --- Command Handler Implementations ---

    def _handle_raw_command(self, params: dict) -> str:
        return self._execute_blocking_task(self.manager.execute_raw_command, params['command'])

    def _handle_apply_settings(self, params: dict) -> None:
        return self._execute_blocking_task(self.manager.apply_settings, params)

    def _handle_start_continuous_acquisition(self, params: dict) -> str:
        if self.state != WorkerState.IDLE:
            raise PermissionError(f"Cannot start acquisition from the current state: {self.state.name}")
        
        self.set_state(WorkerState.CONTINUOUS_ACQUISITION)
        return "Continuous acquisition started."

    def _handle_stop_continuous_acquisition(self, params: dict) -> str:
        if self.state != WorkerState.CONTINUOUS_ACQUISITION:
            # This is not a critical error, just a warning.
            return "Warning: Continuous acquisition is not running."
        
        self.set_state(WorkerState.IDLE)
        return "Continuous acquisition stopped."

    def _handle_set_channel_state(self, params: dict) -> None:
        return self._execute_blocking_task(self.manager.set_channel_state, params['channel'], bool(params['enabled']))

    def _handle_set_channel_volts(self, params: dict) -> None:
        return self._execute_blocking_task(self.manager.set_vertical_scale, params['channel'], float(params['scale']))

    def _handle_set_trigger_slope(self, params: dict) -> None:
        return self._execute_blocking_task(self.manager.set_trigger_slope, params['slope'])

    def _handle_set_trigger_level(self, params: dict) -> None:
        return self._execute_blocking_task(self.manager.set_trigger_level, float(params['level']))

    def _handle_set_acq_state(self, params: dict) -> str:
        state = params.get('state', '').upper()
        if state == 'RUN':
            return self._handle_start_continuous_acquisition({})
        elif state == 'STOP':
            return self._handle_stop_continuous_acquisition({})
        raise ValueError(f"Invalid acquisition state: {state}")

    def _handle_get_device_profile(self, params: dict) -> dict:
        """Returns the loaded device profile dictionary."""
        logging.info("Serving device profile to a client.")
        return self.device_profile