import zmq
import json
import logging
import queue
from PySide6.QtCore import QObject, QThread, Signal, Slot

class ZmqLogHandler(logging.Handler):
    """
    A custom logging handler that publishes log records to a ZMQ PUB socket.
    """
    def __init__(self, pub_socket: zmq.Socket, topic: str = "log"):
        super().__init__()
        self.pub_socket = pub_socket
        self.topic = topic

    def emit(self, record: logging.LogRecord):
        """
        Formats the log record and publishes it over the ZMQ socket.
        """
        # We use format(record) to get the full formatted string,
        # including traceback information for exceptions.
        log_message = self.format(record)
        try:
            self.pub_socket.send_string(self.topic, zmq.SNDMORE)
            self.pub_socket.send_string(log_message)
            print(f"--- ZMQ HANDLER IS FIRING: Sending '{log_message}' on topic '{self.topic}' ---")
        except zmq.ZMQError as e:
            # If ZMQ fails, we can't log it through ZMQ, so print to stderr.
            import sys
            sys.stderr.write(f"CRITICAL: ZmqLogHandler failed to send log: {e}\n")
            sys.stderr.write(f"Original message: {log_message}\n")

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

        # --- Socket for Publishing to the GUI (PUB) ---
        self.gui_pub_socket = self.context.socket(zmq.PUB)
        self.gui_pub_socket.bind(config['local_publish_bind_endpoint'])

        # --- Socket for Publishing to the DIM Server (PUB) ---
        self.dim_pub_socket = self.context.socket(zmq.PUB)
        self.dim_pub_socket.bind(config['dim_publish_endpoint'])

        # --- Poller to manage all readable sockets ---
        self.poller = zmq.Poller()
        self.poller.register(self.dim_socket, zmq.POLLIN)

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


    def reply_to_dim(self, reply: dict):
        """Sends a multipart JSON reply to the DIM server."""
        reply['type'] = 'reply'
        # DEALER must send [delimiter, message] to be routed correctly
        self.dim_socket.send(b'', zmq.SNDMORE)
        self.dim_socket.send_json(reply)

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