import zmq
import json
import logging
import queue
from PySide6.QtCore import QObject, QThread, Signal, Slot


class ZMQCommunicator:
    """
    Encapsulates all ZMQ communication logic for the backend.
    It creates, manages, and polls all sockets, providing a clean
    interface for the main application logic.
    """
    def __init__(self, config: dict):
        self.context = zmq.Context()

        # --- Socket for DIM Server Commands (DEALER) ---
        self.dim_socket = self.context.socket(zmq.DEALER)
        self.dim_socket.connect(config['dim_router_endpoint'])

        # --- Socket for Local GUI Commands (REP) ---
        self.gui_socket = self.context.socket(zmq.REP)
        self.gui_socket.bind(config['local_command_endpoint'])

        # --- Socket for Publishing to the GUI (PUB) ---
        self.gui_pub_socket = self.context.socket(zmq.PUB)
        self.gui_pub_socket.bind(config['local_publish_endpoint'])

        # --- Socket for Publishing to the DIM Server (PUB) ---
        self.dim_pub_socket = self.context.socket(zmq.PUB)
        self.dim_pub_socket.bind(config['dim_publish_endpoint'])

        # --- Poller to manage all readable sockets ---
        self.poller = zmq.Poller()
        self.poller.register(self.dim_socket, zmq.POLLIN)
        self.poller.register(self.gui_socket, zmq.POLLIN)

        logging.info("ZMQCommunicator initialized with 4 sockets.")

    def poll(self, timeout=None) -> dict:
        """
        Polls the sockets for incoming messages.
        Returns a dictionary of sockets that have events.
        """
        return dict(self.poller.poll(timeout))

    def receive_from_dim(self) -> dict:
        """Receives a multipart JSON message from the DIM server's ROUTER."""
        # ROUTER sends [identity, delimiter, message]
        # DEALER receives [delimiter, message]
        _ = self.dim_socket.recv() # Discard the empty delimiter
        msg_raw = self.dim_socket.recv_string()
        return json.loads(msg_raw)

    def receive_from_gui(self) -> dict:
        """Receives a single-part JSON message from the GUI's REQ socket."""
        msg_raw = self.gui_socket.recv_string()
        return json.loads(msg_raw)

    def reply_to_dim(self, reply: dict):
        """Sends a multipart JSON reply to the DIM server."""
        reply['type'] = 'reply'
        # DEALER must send [delimiter, message] to be routed correctly
        self.dim_socket.send(b'', zmq.SNDMORE)
        self.dim_socket.send_json(reply)

    def reply_to_gui(self, reply: dict):
        """Sends a single-part JSON reply to the GUI."""
        self.gui_socket.send_json(reply)

    def publish_to_gui(self, topic: str, payload):
        """Publishes a multipart message (topic, json_payload) to the GUI."""
        self.gui_pub_socket.send_string(topic, zmq.SNDMORE)
        self.gui_pub_socket.send_json(payload)
        logging.info(f"Published to GUI on topic '{topic}'")

    def publish_to_dim(self, topic: str, payload: str):
        """
        Publishes a multipart message (topic, payload) to the DIM server.
        """
        # Step 1: Send the topic string, with the SNDMORE flag to indicate
        # that another part of the message is coming.
        self.dim_pub_socket.send_string(topic, zmq.SNDMORE)
        
        # Step 2: Send the payload string as the final part of the message.
        self.dim_pub_socket.send_string(payload)
        
        logging.info(f"Published to DIM on topic '{topic}'")

    def stop(self):
        """Closes all sockets and terminates the context cleanly."""
        logging.info("Shutting down ZMQCommunicator.")
        for sock in [self.dim_socket, self.gui_socket, self.gui_pub_socket, self.dim_pub_socket]:
            sock.close(linger=0)
        self.context.term()


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
    backend_state_received = Signal(str)

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
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "backend_state")
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
                topic = sub_socket.recv_string()
                data = sub_socket.recv_json()
                
                if topic == "backend_state":
                    self.backend_state_received.emit(data) # data is the state string
                elif topic == "error":
                    self.error_received.emit(data) # data is the error string
                elif topic == "waveform":
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
    backend_state_update = Signal(str)
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
        self.communicator.backend_state_received.connect(self.backend_state_update)
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