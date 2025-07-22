import zmq
import time
from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
import msgpack
import msgpack_numpy as mpack_np

from manager.measurement_manager import MeasurementManager 

# ===================================================================
# The Worker: Performs the blocking measurement task
# ===================================================================
class MeasurementWorker(QObject):
    """
    Performs a single, synchronized measurement cycle with a DIM server.
    This includes a metadata handshake, data transfer, and waiting for an ACK.
    """
    cycle_complete = Signal()
    error = Signal(str)
    status_update = Signal(str)

    def __init__(self, manager: MeasurementManager, dim_endpoint: str, timeout_ms: int):
        super().__init__()
        self.manager = manager
        self.dim_endpoint = dim_endpoint
        self.timeout_ms = timeout_ms
        
        # Each worker thread MUST have its own context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.dim_endpoint)
        
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    @Slot()
    def perform_cycle(self):
        """Executes one full, synchronized measurement cycle."""
        try:
            # 1. Acquire data from the oscilloscope
            self.status_update.emit("Acquiring data from oscilloscope...")
            waveform_data = self.manager.sample(timeout=10)
            if waveform_data is None:
                self.error.emit("Oscilloscope acquisition timed out.")
                return

            # 2. Stage 1: Send metadata and wait for "READY"
            metadata = {
                'points': len(waveform_data),
                'dtype': str(waveform_data.dtype),
                'timestamp': time.time()
            }
            self.status_update.emit(f"Sending metadata: {metadata}")
            self.socket.send_json(metadata)

            if not self.wait_for_reply(b"READY", "Timeout waiting for READY from DIM server."):
                return

            # 3. Stage 2: Send waveform data and wait for "ACK"
            self.status_update.emit("Sending waveform data...")
            
            # Use msgpack for efficient binary data transfer
            waveform_list = waveform_data.tolist()
            packed_data = msgpack.packb(waveform_list, use_bin_type=True)
            self.socket.send(packed_data, copy=False)

            if not self.wait_for_reply(b"ACK", "Timeout waiting for ACK from DIM server."):
                return

            # 4. If all successful, signal completion
            self.status_update.emit("Cycle complete. ACK received.")
            self.cycle_complete.emit()

        except Exception as e:
            self.error.emit(f"An unexpected error occurred: {e}")

    def wait_for_reply(self, expected_reply: bytes, timeout_message: str) -> bool:
        """Uses a poller to wait for a specific reply within a timeout."""
        socks = dict(self.poller.poll(self.timeout_ms))
        if self.socket in socks and socks[self.socket] == zmq.POLLIN:
            reply = self.socket.recv()
            if reply == expected_reply:
                return True
            else:
                self.error.emit(f"Received unexpected reply: {reply.decode()}")
                return False
        else:
            self.error.emit(timeout_message)
            # To prevent ZMQ from getting into a bad state, we should reset the socket
            self.socket.close()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.dim_endpoint)
            self.poller.register(self.socket, zmq.POLLIN)
            return False

    def close(self):
        self.socket.close()
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

    def __init__(self, config, manager: MeasurementManager, parent=None):
        super().__init__(parent)
        self._is_running = False
        
        # Worker and Thread Setup
        self.worker_thread = QThread()
        self.worker = MeasurementWorker(
            manager, 
            config['dim_server_endpoint'], 
            config['ack_timeout_ms']
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        # Connect signals and slots
        self.worker.cycle_complete.connect(self.on_cycle_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.status_update.connect(self.status_update.emit)

    @Slot()
    def start_continuous_cycles(self):
        if self._is_running: return
        self._is_running = True
        self.status_update.emit("Starting continuous cycles...")
        self.worker.perform_cycle()

    @Slot()
    def stop_continuous_cycles(self):
        if not self._is_running: return
        self._is_running = False
        self.status_update.emit("Stopping... The current cycle will be the last.")

    @Slot()
    def on_cycle_finished(self):
        """Called when a full cycle is done. Schedules the next one if still running."""
        if self._is_running:
            # Use a zero-delay timer to start the next cycle immediately
            # without blocking the GUI event loop.
            QTimer.singleShot(0, self.worker.perform_cycle)

    @Slot(str)
    def handle_error(self, error_message):
        self.status_update.emit(f"Error: {error_message}")
        self.stop_continuous_cycles()

    def close(self):
        self.stop_continuous_cycles()
        self.worker_thread.quit()
        self.worker_thread.wait(3000)
        self.worker.close() # Ensure worker's ZMQ resources are freed
        print("Server manager closed cleanly.")