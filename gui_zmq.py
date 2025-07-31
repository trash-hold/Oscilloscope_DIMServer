from zmq_server.server import Server
from zmq_server.gui.dashboard import OscilloscopeMonitorGUI
import sys
import threading

from PySide6.QtWidgets import (
    QApplication
)

CONFIG_PATH = "secret/config.json"

def run_server(config_path):
    """
    This function will be the target for our server thread.
    It simply creates an instance of the Server, which then runs.
    """
    print("Starting ZMQ server in a background thread...")
    server = Server(config_path)
    # The server's blocking loop is now running inside this thread.
    print("ZMQ server thread finished.") 


if __name__=="__main__":
    server_thread = threading.Thread(
        target=run_server, args=(CONFIG_PATH,), daemon=True
    )

    # 2. Start the server thread. It will run in the background.
    server_thread.start()

    print("Starting GUI in the main thread...")
    app = QApplication(sys.argv)
    window = OscilloscopeMonitorGUI(CONFIG_PATH)
    window.show()
    sys.exit(app.exec())
    