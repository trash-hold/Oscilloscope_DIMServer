import zmq
import numpy as np
import time

# --- Configuration ---
SERVER_ENDPOINT = "tcp://localhost:5555"
DATA_POINTS = 3000
SEND_INTERVAL_SECONDS = 2

def main():
    """
    Connects to the C++ server and periodically sends a NumPy array of floats.
    """
    print("Starting Python data sender...")
    
    try:
        context = zmq.Context()
        # Create a REQ (Request) socket
        socket = context.socket(zmq.REQ)
        socket.connect(SERVER_ENDPOINT)
        print(f"Connected to server at {SERVER_ENDPOINT}")

        # Main loop to send data
        message_count = 0
        while True:
            # 1. Generate sample data
            # Use np.float32 to match the 'float' type in C++ (typically 4 bytes)
            data_array = np.linspace(
                start=message_count, 
                stop=message_count + 100, 
                num=DATA_POINTS, 
                dtype=np.float32
            )

            # 2. Send the data as raw bytes
            # The .tobytes() method provides direct access to the underlying data buffer
            print(f"Sending {data_array.size} floats ({data_array.nbytes} bytes)...")
            socket.send(data_array.tobytes())

            # 3. Wait for the reply from the server
            reply = socket.recv_string()
            print(f"Received reply: '{reply}'\n")
            
            message_count += 1
            time.sleep(SEND_INTERVAL_SECONDS)

    except zmq.ZMQError as e:
        print(f"ZeroMQ Error: {e}")
    except KeyboardInterrupt:
        print("\nSender stopped by user.")
    finally:
        # Clean up
        if 'socket' in locals():
            socket.close()
        if 'context' in locals():
            context.term()
        print("Cleanup complete. Exiting.")


if __name__ == "__main__":
    main()