import zmq
import json
import logging
import time
from enum import Enum, auto

# Assuming these are in your project structure
from manager.measurement_manager import MeasurementManager
from drivers.TDS3054C import TDS3054C # Replace with your actual driver
from common.exepction import * # Your custom exceptions

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WorkerState(Enum):
    """Defines the possible operational states of the backend worker."""
    IDLE = auto()
    BUSY = auto()
    CONTINUOUS_ACQUISITION = auto()

class BackendWorker:
    """
    The core of the headless backend. It manages device state, handles commands
    from both remote (DIM) and local (GUI) clients, and has no GUI dependencies.
    """
    def __init__(self, manager: MeasurementManager, config: dict):
        self.manager = manager
        self.state = WorkerState.IDLE
        self.config = config

        # --- Command Dispatcher Map ---
        self.COMMAND_MAP = {
            'raw_query': self._handle_raw_query,
            'raw_write': self._handle_raw_write,
            'apply_settings': self._handle_apply_settings,
            'start_continuous_acquisition': self._handle_start_continuous_acquisition,
            'stop_continuous_acquisition': self._handle_stop_continuous_acquisition,
            'set_channel_state': self._handle_set_channel_state,
            'set_channel_volts': self._handle_set_channel_volts,
            'set_trigger_edge': self._handle_set_trigger_edge,
            'set_trigger_level': self._handle_set_trigger_level,
        }

        # --- ZMQ Context and Sockets ---
        logging.info("Initializing ZMQ sockets...")
        self.context = zmq.Context()
        
        # Socket to talk to the remote C++ DIM server
        self.dim_socket = self.context.socket(zmq.DEALER)
        self.dim_socket.connect(config['dim_server_endpoint'])

        # Socket to listen for commands from local clients (e.g., the GUI)
        self.local_cmd_socket = self.context.socket(zmq.REP)
        self.local_cmd_socket.bind(config['local_command_endpoint'])

        # Socket to publish asynchronous updates (status, data) to local clients
        self.local_pub_socket = self.context.socket(zmq.PUB)
        self.local_pub_socket.bind(config['local_publish_endpoint'])

        # --- Poller to handle multiple sockets concurrently ---
        self.poller = zmq.Poller()
        self.poller.register(self.dim_socket, zmq.POLLIN)
        self.poller.register(self.local_cmd_socket, zmq.POLLIN)
        logging.info("Backend worker initialized successfully.")

    def set_state(self, new_state: WorkerState):
        """A new helper function to change state and publish the update."""
        if self.state == new_state:
            return # No change
        
        self.state = new_state
        logging.info(f"STATE CHANGE: {self.state.name}")
        # Publish the new state with a 'backend_state' topic
        self.local_pub_socket.send_string(f"backend_state {self.state.name}")

    def publish_status(self, message: str):
        """Helper to log and publish a status update."""
        logging.info(f"STATUS: {message}")
        self.local_pub_socket.send_string(f"status {json.dumps(message)}")

    def publish_error(self, message: str):
        """Helper to log and publish an error message."""
        logging.error(f"ERROR: {message}")
        self.local_pub_socket.send_string(f"error {json.dumps(message)}")

    def run(self):
        # --- SEND THE INITIAL HANDSHAKE ---
        logging.info("Sending handshake message to DIM server...")
        try:
            handshake_msg = {"type": "handshake", "payload": "Python client is online"}
            self.dim_socket.send(b'', zmq.SNDMORE) 
            self.dim_socket.send_json(handshake_msg)
            self.publish_status("Handshake sent to DIM server.")
        except zmq.ZMQError as e:
            self.publish_error(f"Could not send handshake to DIM server: {e}")
        
        self.publish_status(f"Backend worker started. State: {self.state.name}")
        
        while True:
            try:
                if self.state == WorkerState.CONTINUOUS_ACQUISITION:
                    self._perform_one_acquisition_cycle()
                    sockets_with_data = dict(self.poller.poll(0))
                else:
                    sockets_with_data = dict(self.poller.poll())

                if self.dim_socket in sockets_with_data:
                    # When receiving from a ROUTER, the first part is the empty delimiter
                    _ = self.dim_socket.recv() # We receive and discard the delimiter
                    msg = self.dim_socket.recv_string()
                    reply = self._dispatch_request(msg)
                    reply['type'] = 'reply' 
                    self.dim_socket.send(b'', zmq.SNDMORE)
                    self.dim_socket.send_json(reply)

                if self.local_cmd_socket in sockets_with_data:
                    msg = self.local_cmd_socket.recv_string()
                    reply = self._dispatch_request(msg)
                    self.local_cmd_socket.send_json(reply)

            except KeyboardInterrupt:
                logging.info("Shutdown signal received. Exiting...")
                break
            except Exception as e:
                logging.critical(f"An unhandled exception occurred in the main loop: {e}", exc_info=True)
                self.state = WorkerState.IDLE
                self.publish_error(f"Critical error: {e}. Returning to IDLE state.")

    def _dispatch_request(self, message_raw: str) -> dict:
        """Parses a request, checks state, calls the handler, and returns a JSON reply."""
        logging.debug(f"Dispatching request in state {self.state.name}: {message_raw}")
        payload = {}
        command_name = "[unknown]"

        try:
            request = json.loads(message_raw)
            command_name = request.get("command")
            params = request.get("params", {})
            
            # --- State Machine Gatekeeper ---
            if self.state == WorkerState.CONTINUOUS_ACQUISITION and command_name != 'stop_continuous_acquisition':
                payload = {"status": "error", "message": "Command not allowed during continuous acquisition."}
            elif self.state == WorkerState.BUSY:
                payload = {"status": "error", "message": "Device is busy with another command."}
            else:
                handler = self.COMMAND_MAP.get(command_name)
                if not handler:
                    payload = {"status": "error", "message": f"Command '{command_name}' not found."}
                else:
                    result = handler(params)
                    payload = {"status": "ok", "payload": result or "Command executed successfully."}

        except json.JSONDecodeError:
            payload = {"status": "error", "message": "Malformed JSON request."}
        except Exception as e:
            logging.critical(f"An internal error occurred while processing command '{command_name}': {e}", exc_info=True)
            payload = {"status": "error", "message": f"An internal Python error occurred: {e}"}
        
        logging.info(f"Returning reply: {payload}")
        return payload

    def _execute_blocking_task(self, func, *args, **kwargs):
        """A safe wrapper for short tasks that ensures state is managed correctly."""
        self.state = WorkerState.BUSY
        self.publish_status(f"State changed to BUSY for task: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            self.state = WorkerState.IDLE
            self.publish_status(f"State changed to IDLE.")

    # --- Command Handler Implementations ---

    def _handle_raw_query(self, params: dict) -> str:
        return self._execute_blocking_task(self.manager.query, params['query'])

    def _handle_raw_write(self, params: dict) -> None:
        return self._execute_blocking_task(self.manager.write, params['command'])

    def _handle_apply_settings(self, params: dict) -> None:
        return self._execute_blocking_task(self.manager.apply_settings, params)

    def _handle_start_continuous_acquisition(self, params: dict) -> str:
        if self.state != WorkerState.IDLE:
            raise RuntimeError(f"Cannot start acquisition while in {self.state.name} state.")
        self.state = WorkerState.CONTINUOUS_ACQUISITION
        self.publish_status("State changed to CONTINUOUS_ACQUISITION.")
        return "Continuous acquisition started."

    def _handle_stop_continuous_acquisition(self, params: dict) -> str:
        if self.state != WorkerState.CONTINUOUS_ACQUISITION:
            return "Warning: Continuous acquisition is not running."
        self.state = WorkerState.IDLE
        self.publish_status("State changed to IDLE.")
        return "Continuous acquisition stopped."

    def _handle_set_channel_state(self, params: dict) -> None:
        # Expected params: {"channel": 1, "state": "ON"}
        ch = params['channel']
        state = params['state'].upper() == 'ON' # Convert to boolean
        # self.manager.dev.set_channel_state(ch, state) // Real call
        return self._execute_blocking_task(self.manager.set_channel_state, ch, state)

    def _handle_set_channel_volts(self, params: dict) -> None:
        # Expected params: {"channel": 1, "volts": 2.2e-1}
        ch = params['channel']
        volts = float(params['volts'])
        # self.manager.dev.set_vertical_scale(ch, volts) // Real call
        return self._execute_blocking_task(self.manager.set_vertical_scale, ch, volts)

    def _handle_set_trigger_edge(self, params: dict) -> None:
        # Expected params: {"edge": "RISING"}
        edge = params['edge']
        # self.manager.dev.set_trigger(slope=edge) // Real call
        return self._execute_blocking_task(self.manager.set_trigger_slope, edge)

    def _handle_set_trigger_level(self, params: dict) -> None:
        # Expected params: {"level": 1.5}
        level = float(params['level'])
        # self.manager.dev.set_trigger(level=level) // Real call
        return self._execute_blocking_task(self.manager.set_trigger_level, level)

    def _perform_one_acquisition_cycle(self):
        """Acquires data and publishes it on the PUB socket."""
        try:
            self.publish_status("Acquiring waveform...")
            waveform_data = self.manager.sample(timeout=10)
            
            # Publish waveform data with a "waveform" topic
            # Note: msgpack is more efficient for numpy arrays if you have it
            self.local_pub_socket.send_string("waveform", zmq.SNDMORE)
            self.local_pub_socket.send_json({"points": len(waveform_data), "data": waveform_data.tolist()})

        except AcquisitionTimeoutError as e:
            self.publish_error(f"Acquisition Timeout: {e}")
            # Don't stop the loop, just report the timeout
        except Exception as e:
            self.publish_error(f"Error in acquisition cycle: {e}")
            # On other errors, stop the acquisition to be safe
            self.state = WorkerState.IDLE
            self.publish_status("Acquisition stopped due to an error.")