from zmq_server.common.driver_map import create_driver
from zmq_server.drivers.AbstractInterfaces import Oscilloscope
import json
import numpy as np
from datetime import datetime
import os

CONFIG = './secret/TDS3054C_profile.json'
TITLE_PREFIX = "PMT0_NORMAL_1400V_"
SAVE_DIRECTORY = "./data/"

def display_help():
    """Prints a list of available commands."""
    print("\nAvailable commands:")
    print("  a          - Start a single acquisition sequence.")
    print("  s          - Save the last acquired waveform from channel 1 to a CSV file.")
    print("  ch <prefix> - Change the title prefix for saved files.")
    print("  help       - Display this help message.")
    print("  exit       - Terminate the program.\n")

if __name__ == "__main__":
    # Create the save directory if it doesn't exist
    if not os.path.exists(SAVE_DIRECTORY):
        os.makedirs(SAVE_DIRECTORY)
        print(f"Created directory: {SAVE_DIRECTORY}")

    with open(CONFIG, 'r') as f:
        config = json.load(f)

    try:
        osc: Oscilloscope = create_driver("TDS3054C", config["connection_params"])
        if not osc.test_connection():
            print("Device not responding. Exiting.")
            exit()
    except Exception as e:
        print(f"Failed to connect to the device: {e}")
        exit()

    print("Connection successful. Type 'help' for a list of commands.")
    
    usr_input = ''
    while True:
        usr_input = input("> ").strip()
        parts = usr_input.lower().split()
        command = parts[0] if parts else ""

        if command == "exit":
            print("Exiting program.")
            break

        elif command == "help":
            display_help()

        # For acquiring one sample
        elif command == "a":
            try:
                print("Starting single acquisition...")
                osc.sample()
                print("Acquisition complete. Use 's' to save the waveform.")
            except Exception as e:
                print(f"An error occurred during acquisition: {e}")

        # For saving already acquired waveform (for simplicity only @ channel 1)
        elif command == "s":
            try:
                print("Fetching waveform from channel 1...")
                waveform_data = osc.get_waveform(1)
                
                if waveform_data is not None:
                    # Generate a timestamp for the filename
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    filename = f"{TITLE_PREFIX}_{timestamp}.csv"
                    filepath = os.path.join(SAVE_DIRECTORY, filename)
                    
                    # Save the numpy array to a CSV file
                    np.savetxt(filepath, waveform_data, delimiter=',')
                    print(f"Waveform saved to {filepath}")
                else:
                    print("Failed to retrieve waveform.")
            except Exception as e:
                print(f"An error occurred while saving the waveform: {e}")

        # For changing the prefix
        elif command == "ch":
            if len(parts) > 1:
                TITLE_PREFIX = parts[1]
                print(f"Title prefix changed to: {TITLE_PREFIX}")
            else:
                print("Usage: ch <new_prefix>")
        
        elif not command:
            # If the user just presses Enter, do nothing
            pass

        else:
            print(f"Unknown command: '{command}'. Type 'help' for a list of commands.")