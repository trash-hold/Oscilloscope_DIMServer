from PySide6.QtCore import QObject, QThread, Signal, Slot
import zmq
import queue
import logging
import json


class GuiCommunicator(QObject):
    """
    Runs in a QThread. Subscribes to all informational topics from the backend.
    """
    # Signals for different types of data received from the backend
    log_received = Signal(str)
    backend_state_received = Signal(str)
    error_received = Signal(str)
    waveform_received = Signal(dict)

    def __init__(self, config: dict, context: zmq.Context):
        super().__init__()
        self.config = config
        self._is_running = True
        self.context = context

    @Slot()
    def run_communication_loop(self):
        """The main loop for the communicator thread."""
        sub_socket = self.context.socket(zmq.SUB)
        
        connect_address = self.config['local_publish_connect_address']
        sub_socket.connect(connect_address)
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "") 
        logging.info(f"GUI subscriber connected to {connect_address} and listening for all topics.")

        # Set a timeout on the receive call so the loop can check _is_running
        sub_socket.setsockopt(zmq.RCVTIMEO, 1000) 

        while self._is_running:
            try:
                # Block until a message is received
                topic = sub_socket.recv_string()
                payload = sub_socket.recv_string() # Assuming logs are strings now
                # For debug
                #print(f"--- GUI LISTENER RECEIVED: Topic='{topic}', Payload='{payload}' ---")

                if topic == "log":
                    self.log_received.emit(payload)
                elif topic == "backend_state":
                    # The log handler will already capture the state change,
                    # but a dedicated topic is good for driving specific UI elements.
                    self.backend_state_received.emit(payload) 
                elif topic == "error":
                    # This topic can be used for critical errors that need special handling
                    self.error_received.emit(payload)
                elif topic == "waveform":
                    # Waveform data is JSON
                    self.waveform_received.emit(json.loads(payload))

            except zmq.Again:
                # This is not an error, it's just the timeout.
                # The loop will continue and check _is_running again.
                continue 
            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    logging.info("ZMQ context terminated, shutting down listener.")
                    break
                else:
                    logging.error(f"ZMQ Error in GUI listener: {e}")
                    self.error_received.emit(f"ZMQ Error: {e}")
                    QThread.msleep(1000)

        sub_socket.close()
        # DO NOT terminate the context here, the ServerManager owns it.
        logging.info("GUI Communicator loop finished.")

    @Slot()
    def stop(self):
        """Signals the loop to terminate."""
        self._is_running = False


class ServerManager(QObject):
    """
    The main interface for the GUI. It orchestrates the GuiCommunicator thread.
    This class is now much simpler.
    """
    # Expose signals for the GUI
    log_update = Signal(str)
    backend_state_update = Signal(str)
    error_occurred = Signal(str)
    waveform_update = Signal(dict)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.zmq_context = zmq.Context()
        self.worker_thread = QThread()
        self.communicator = GuiCommunicator(config, self.zmq_context)

        self.communicator.moveToThread(self.worker_thread)

        # Connect signals from the communicator to the manager's signals
        self.communicator.log_received.connect(self.log_update)
        self.communicator.backend_state_received.connect(self.backend_state_update)
        self.communicator.error_received.connect(self.error_occurred)
        self.communicator.waveform_received.connect(self.waveform_update)

        self.worker_thread.started.connect(self.communicator.run_communication_loop)
        self.worker_thread.start()
        logging.info("ServerManager started and moved GuiCommunicator to a new thread.")

    def close(self):
        """Shuts down the communicator thread cleanly."""
        if self.worker_thread.isRunning():
            logging.info("Stopping communicator thread...")
            self.communicator.stop()
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000):
                logging.warning("Communicator thread did not shut down cleanly.")
            else:
                logging.info("Communicator thread shut down successfully.")