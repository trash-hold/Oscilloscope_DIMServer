from zmq_server.server import Server

CONFIG_PATH = "secret/config.json"

if __name__=="__main__":
    server = Server(CONFIG_PATH)
    