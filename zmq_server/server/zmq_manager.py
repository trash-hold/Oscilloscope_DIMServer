import json
import zmq
import time
import logging      # For Error handling
from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer   # Integration with GUI
import msgpack
import msgpack_numpy as mpack_np
from common.exepction import *

from manager.measurement_manager import MeasurementManager 

class CommandWorker(QObject):
    """
    Runs in a dedicated thread, listening for commands from the C++
    DIM server via a ZMQ DEALER socket. It executes commands and
    sends replies back.
    """
    status_update = Signal(str)
    error = Signal(dict)

    def __init__(self, manager: MeasurementManager, dim_endpoint: str):
        super().__init__()
        self.manager = manager
        self.dim_endpoint = dim_endpoint
        self._is_running = False

        # Each worker thread MUST have its own context and socket
        self.context = zmq.Context()
        # <--- CHANGE: Use DEALER socket for asynchronous, bidirectional communication --->
        self.socket = self.context.socket(zmq.DEALER)
        self.poller = zmq.Poller()

    @Slot()
    def run(self):
        """
        The main loop for the worker thread. Connects the socket and
        continuously polls for incoming messages.
        """
        self.status_update.emit("Worker thread started. Connecting to C++ server...")
        self.socket.connect(self.dim_endpoint)
        self.poller.register(self.socket, zmq.POLLIN)
        self._is_running = True
        
        # Send an initial "hello" so the ROUTER knows our identity
        self.socket.send_json({"type": "status", "payload": "Python worker connected"})

        while self._is_running:
            # Poll for messages with a timeout (e.g., 100ms)
            socks = dict(self.poller.poll(100))
            if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                # A DEALER socket receives a multi-part message from a ROUTER
                # The first part is an empty delimiter, the second is the content
                _, msg_bytes = self.socket.recv_multipart()
                self.handle_message(msg_bytes)

        # Clean shutdown
        self.socket.close()
        self.context.term()
        self.status_update.emit("Worker thread stopped.")

    def handle_message(self, msg_bytes: bytes):
        """Parses an incoming message and routes it to the correct handler."""
        try:
            message = json.loads(msg_bytes.decode('utf-8'))
            msg_type = message.get("type")

            if msg_type == "command":
                self.handle_device_command(message)
            else:
                logging.warning(f"Received unknown message type: {msg_type}")
                self.status_update.emit(f"Warning: Received unknown message type '{msg_type}'")

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logging.error(f"Failed to parse incoming message: {e}")
            self.error.emit(ProtocolError(f"Malformed message received: {e}").to_dict())

    def handle_device_command(self, message: dict):
        """Executes a raw command on the device and sends a reply."""
        cmd_id = message.get("id", "unknown")
        command = message.get("payload")

        if not command:
            self.send_reply(cmd_id, "Error: Command payload was empty.", is_error=True)
            return

        self.status_update.emit(f"Executing command: {command}")
        try:
            # Use our new generic method in the manager
            result = self.manager.execute_raw_command(command)
            self.send_reply(cmd_id, result)

        except DeviceError as e:
            self.status_update.emit(f"Error executing '{command}': {e}")
            self.send_reply(cmd_id, str(e), is_error=True)
        except Exception as e:
            logging.critical(f"Unhandled exception during command execution: {e}", exc_info=True)
            self.send_reply(cmd_id, f"An unexpected internal error occurred: {e}", is_error=True)

    def send_reply(self, cmd_id: str, payload: str, is_error: bool = False):
        """Constructs and sends a JSON reply to the C++ server."""
        reply = {
            "type": "reply",
            "id": cmd_id,
            "payload": payload,
            "error": is_error
        }
        self.socket.send_json(reply)

    @Slot()
    def stop(self):
        """Signals the main loop to terminate."""
        self._is_running = False


# ===================================================================
# The Worker: Performs the blocking measurement task
# ===================================================================
class MeasurementWorker(QObject):
    """
    Performs a single, synchronized measurement cycle with a DIM server.
    This includes a metadata handshake, data transfer, and waiting for an ACK.
    """
    cycle_complete = Signal()
    config_applied = Signal()
    error = Signal(dict)
    status_update = Signal(str)

    def __init__(self, manager: MeasurementManager, dim_endpoint: str, zmq_timeout: int):
        super().__init__()
        self.manager = manager
        self.dim_endpoint = dim_endpoint
        self.zmq_timeout = zmq_timeout    #ZMQ socket timeout
        self.acquisition_timeout = 10   
        
        # Each worker thread MUST have its own context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.dim_endpoint)
        
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    @Slot(int)
    def set_acquisition_timeout(self, timeout: int):
        """Sets the timeout for the oscilloscope data acquisition."""
        self.acquisition_timeout = timeout

    @Slot()
    def perform_cycle(self):
        """Executes one full, synchronized measurement cycle."""
        try:
            # 1. Acquire data from the oscilloscope
            self.status_update.emit("Acquiring data from oscilloscope...")
            waveform_data = self.manager.sample(timeout=self.acquisition_timeout)

            # 2. Stage 1: Send metadata and wait for "READY"
            metadata = {
                'points': len(waveform_data),
                'dtype': str(waveform_data.dtype),
                'timestamp': time.time()
            }
            self.status_update.emit(f"Sending metadata: {metadata}")
            self.socket.send_json(metadata)

            self.wait_for_reply(b"READY")


            # 3. Stage 2: Send waveform data and wait for "ACK"
            self.status_update.emit("Sending waveform data...")
            
            # Use msgpack for efficient binary data transfer
            waveform_list = waveform_data.tolist()
            packed_data = msgpack.packb(waveform_list, use_bin_type=True)
            self.socket.send(packed_data, copy=False)

            self.wait_for_reply(b"ACK")

            # 4. If all successful, signal completion
            self.status_update.emit("Cycle complete. ACK received.")
            self.cycle_complete.emit()

        except (AcquisitionError, ZMQCommunicationError, ConfigurationError) as e:
            logging.warning(f"A known error occurred during the cycle: {e}")
            self.error.emit(e.to_dict())

        except Exception as e:
            logging.critical("An unexpected error occurred in the measurement worker!", exc_info=True)
            error = UnhandledWorkerException(
                f'An unexpected internal error occurred: {e}'
            )
            self.error.emit(error.to_dict())

    @Slot(dict)
    def apply_new_config(self, settings: dict):
        """Applies new measurement parameters via the manager."""
        try:
            self.status_update.emit("Applying new measurement settings...")
            self.manager.apply_settings(settings)
            self.status_update.emit("Settings successfully applied.")
            self.config_applied.emit()
        except Exception as e:
            # Handle potential errors during configuration
            logging.error(f"Failed to apply settings: {e}", exc_info=True)
            self.error.emit({
                'type': 'ConfigurationError',
                'message': f'Failed to apply new settings: {e}'
            })

    def wait_for_reply(self, expected_reply: bytes) -> bool:
        """Uses a poller to wait for a specific reply within a timeout."""
        socks = dict(self.poller.poll(self.zmq_timeout))
        if self.socket in socks and socks[self.socket] == zmq.POLLIN:
            reply = self.socket.recv()
            if reply == expected_reply:
                return # Success
            else:
                raise ZMQCommunicationError(f"Received unexpected reply: '{reply.decode()}'")
        else:
            # To prevent ZMQ from getting into a bad state, reset the socket on timeout.
            self.socket.close(linger=0)
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.dim_endpoint)
            self.poller.unregister(self.socket) # Unregister old socket
            self.poller.register(self.socket, zmq.POLLIN) # Register new one
            raise ZMQTimeoutError(f"Timeout waiting for '{expected_reply.decode()}' from DIM server.")

    def close(self):
        if not self.socket.closed:
            self.socket.close(linger=0)
        self.context.term()


# ===================================================================
# The Manager: Orchestrates everything without blocking the GUI
# ===================================================================
class ServerManager(QObject):
    """
    Manages the CommandWorker thread.
    """
    status_update = Signal(str)
    error_occurred = Signal(dict)

    def __init__(self, config, manager: MeasurementManager, parent=None):
        super().__init__(parent)
        
        # Worker and Thread Setup
        self.worker_thread = QThread()
        self.worker = CommandWorker(
            manager,
            config['dim_server_endpoint']
        )
        self.worker.moveToThread(self.worker_thread)

        # Connect signals and slots
        self.worker.status_update.connect(self.status_update)
        self.worker.error.connect(self.error_occurred)
        
        # When the thread starts, call the worker's run method
        self.worker_thread.started.connect(self.worker.run)
        
        # Start the thread
        self.worker_thread.start()

    def close(self):
        """Shuts down the worker thread cleanly."""
        if self.worker_thread.isRunning():
            # Tell the worker's loop to stop
            self.worker.stop()
            # Wait for the thread to finish gracefully
            if not self.worker_thread.wait(3000):
                logging.warning("Worker thread did not shut down cleanly.")
                self.worker_thread.terminate() # Force terminate if it's stuck
        print("Server manager closed cleanly.")

'''
# ===================================================================
# The Manager: Orchestrates everything without blocking the GUI
# ===================================================================
class ServerManager(QObject):
    """
    Manages the worker thread and the continuous measurement loop using
    a non-blocking, one-shot timer pattern.
    """
    status_update = Signal(str)
    error_occurred = Signal(dict)
    _config_update_request = Signal(dict)

    def __init__(self, config, manager: MeasurementManager, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._continue_on_timeout = False
        self._pending_settings = None 
        
        # Worker and Thread Setup
        self.worker_thread = QThread()
        self.worker = MeasurementWorker(
            manager, 
            config['dim_server_endpoint'], 
            config['ack_zmq_timeout']
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        # Connect signals and slots
        self.worker.cycle_complete.connect(self.on_cycle_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.status_update.connect(self.status_update.emit)
        self._config_update_request.connect(self.worker.apply_new_config)
        self.worker.config_applied.connect(self.on_config_applied)

    @Slot(int, bool)
    def start_continuous_cycles(self, acquisition_timeout: int, continue_on_timeout: bool):
        if self._is_running: return
        self._is_running = True
        self._continue_on_timeout = continue_on_timeout
        self.status_update.emit("Starting continuous cycles...")
        QTimer.singleShot(0, lambda: self.worker.set_acquisition_timeout(acquisition_timeout))
        
        if self._pending_settings:
            self._apply_pending_config()
            # The on_config_applied slot will kick off the first measurement.
        else:
            # Otherwise, start measuring immediately.
            QTimer.singleShot(0, self.worker.perform_cycle)

    @Slot()
    def stop_continuous_cycles(self):
        if not self._is_running: return
        self._is_running = False

    @Slot()
    def on_cycle_finished(self):
        """
        Called when a measurement cycle is done. This is the ideal time
        to check for and apply pending configuration changes.
        """
        if self._pending_settings:
            # If there are pending settings, apply them instead of starting a new cycle.
            self._apply_pending_config()
            # The on_config_applied slot will then be responsible for restarting the loop.
            return

        # If no pending settings, continue the loop as normal.
        if self._is_running:
            QTimer.singleShot(0, self.worker.perform_cycle)
            
    @Slot()
    def on_config_applied(self):
        """
        Called after settings have been successfully applied. If the system
        was running, this method restarts the measurement loop.
        """
        # If we were in a continuous run, resume it with the new settings.
        if self._is_running:
            self.status_update.emit("Resuming continuous measurement...")
            QTimer.singleShot(0, self.worker.perform_cycle)

    @Slot(dict)
    def update_measurement_config(self, settings: dict):
        """
        Public slot to receive settings from the GUI or other sources.
        It stores the settings and applies them at a safe time.
        """
        self.status_update.emit("Settings update requested. Will apply when ready.")
        self._pending_settings = settings
        
        # If the measurment is not running, the change can be applied immediately
        if not self._is_running:
            self._apply_pending_config()

    @Slot(dict)
    def handle_error(self, error_data: dict):
        # Strip data from error
        error_message = error_data.get('message', 'An unknown error occurred.')
        error_type = error_data.get('type', 'UnknownError')

        # Update GUI
        self.status_update.emit(f"Error ({error_type}): {error_message}")
        self.error_occurred.emit(error_data)

        if error_type == "AcquisitionTimeoutError" and self._continue_on_timeout:
            # Schedule the next cycle and do nothing else.
            # The GUI will log the warning, but the process continues.
            if self._is_running:
                QTimer.singleShot(0, self.worker.perform_cycle)
        else:
            self.stop_continuous_cycles()

    def _apply_pending_config(self):
        """Internal method to trigger the application of pending settings."""
        if self._pending_settings:
            self._config_update_request.emit(self._pending_settings)
            self._pending_settings = None 

    def close(self):
        if self.worker_thread.isRunning():
            self.stop_continuous_cycles()
            QTimer.singleShot(0, self.worker.close) # Ask worker to close its resources
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000):
                logging.warning("Worker thread did not shut down cleanly.")
        print("Server manager closed cleanly.")
'''