import zmq
import json
import logging
import queue
from PySide6.QtCore import QObject, QThread, Signal, Slot

class GuiCommunicator(QObject):
    """
    Runs in a QThread within the GUI application. Handles all ZMQ communication
    with the backend, keeping the main GUI thread responsive.
    """
    # Signals to send data/status updates to the main GUI thread
    status_received = Signal(str)
    error_received = Signal(str)
    waveform_received = Signal(dict)
    command_reply_received = Signal(dict)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self._is_running = True
        self.command_queue = queue.Queue()

    @Slot()
    def run_communication_loop(self):
        """The main loop for the communicator thread."""
        context = zmq.Context()
        
        # REQ socket for sending commands
        cmd_socket = context.socket(zmq.REQ)
        cmd_socket.connect(self.config['local_command_endpoint'])

        # SUB socket for receiving async updates
        sub_socket = context.socket(zmq.SUB)
        sub_socket.connect(self.config['local_publish_endpoint'])
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "status")
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "error")
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "waveform")

        poller = zmq.Poller()
        poller.register(sub_socket, zmq.POLLIN)

        while self._is_running:
            # 1. Check for commands from the GUI to send to the backend
            try:
                command_to_send = self.command_queue.get_nowait()
                logging.info(f"Sending command: {command_to_send}")
                cmd_socket.send_json(command_to_send)
                reply = cmd_socket.recv_json()
                logging.info(f"Received reply: {reply}")
                self.command_reply_received.emit(reply)
            except queue.Empty:
                pass # No commands to send
            except zmq.ZMQError as e:
                self.error_received.emit(f"ZMQ Error sending command: {e}")

            # 2. Poll for asynchronous messages from the backend (non-blocking)
            socks = dict(poller.poll(100)) # Poll for 100ms
            if sub_socket in socks:
                topic, message_raw = sub_socket.recv_string().split(' ', 1)
                data = json.loads(message_raw)
                if topic == "status":
                    self.status_received.emit(data)
                elif topic == "error":
                    self.error_received.emit(data)
                elif topic == "waveform":
                    # For real data, you might receive raw bytes (msgpack)
                    # For this example, we assume JSON
                    self.waveform_received.emit(data)

        cmd_socket.close()
        sub_socket.close()
        context.term()
        logging.info("GUI Communicator shut down cleanly.")

    @Slot()
    def stop(self):
        """Signals the loop to terminate."""
        self._is_running = False

    # --- Public slots for the GUI to call ---

    @Slot(dict)
    def send_command(self, command_dict: dict):
        """Generic slot to queue any command for sending."""
        self.command_queue.put(command_dict)


class ServerManager(QObject):
    """
    The main interface for the GUI. It orchestrates the GuiCommunicator thread
    and provides a clean API for the main window to use.
    """
    # Expose signals for the GUI
    status_update = Signal(str)
    error_occurred = Signal(str)
    waveform_update = Signal(dict)
    reply_update = Signal(dict)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.worker_thread = QThread()
        self.communicator = GuiCommunicator(config)
        
        self.communicator.moveToThread(self.worker_thread)

        # Connect signals from the communicator to the manager's signals
        self.communicator.status_received.connect(self.status_update)
        self.communicator.error_received.connect(self.error_occurred)
        self.communicator.waveform_received.connect(self.waveform_update)
        self.communicator.command_reply_received.connect(self.reply_update)

        # Connect thread management signals
        self.worker_thread.started.connect(self.communicator.run_communication_loop)
        
        self.worker_thread.start()
        logging.info("ServerManager started and moved GuiCommunicator to a new thread.")

    def close(self):
        """Shuts down the communicator thread cleanly."""
        if self.worker_thread.isRunning():
            self.communicator.stop()
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000):
                logging.warning("Communicator thread did not shut down cleanly.")

    # --- High-level methods for the GUI to call ---

    @Slot()
    def start_continuous(self):
        cmd = {"command": "start_continuous_acquisition", "params": {}}
        self.communicator.send_command(cmd)

    @Slot()
    def stop_continuous(self):
        cmd = {"command": "stop_continuous_acquisition", "params": {}}
        self.communicator.send_command(cmd)

    @Slot(dict)
    def apply_settings(self, settings: dict):
        cmd = {"command": "apply_settings", "params": settings}
        self.communicator.send_command(cmd)

    @Slot(str)
    def send_raw_query(self, query: str):
        cmd = {"command": "raw_query", "params": {"query": query}}
        self.communicator.send_command(cmd)

'''
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