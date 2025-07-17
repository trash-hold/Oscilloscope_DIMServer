
from zmq_server.drivers.AbstractInterfaces import Oscilloscope     #Oscilloscope interface class
import json     # For reading config files
import time     # For implementing timeouts

class MeasurementManager():
    def __init__(self, dev:Oscilloscope, json_file:str = None):
        # Basic handles
        self.dev = dev     # Child of abstract class Oscilloscope
        self.config = self.load_config(json_file) if json_file is not None else None

    def start_connection(self) -> None:
        self.dev.start_connection()

    def load_config(self, json_file: str) -> dict:
        '''
        Connect and configure the oscilloscope according to the defined json file.
        '''
        
        # Load the file
        config = None
        with open(json_file, 'r') as file:
            config = json.load(file)
            file.close()

        # Connect to device
        if self.dev is None:
            try:
                if self.dev.test_connection() == False:
                    raise ConnectionError("COM: The port specified in the config file is wrong or unavailable!")

                self.dev.config(json_file)

            except:
                raise ConnectionError("COM: The port specified in the config file is wrong or unavailable!")

        self.config = config

        print("Successfully configured the oscilloscope!")
        return config
    

    
    def sample(self, timeout: int = 60) -> None:
        '''
        Runs oscilloscope in single sequence mode and waits for a single acquistion -- has timeout feature. If you want to turn off the timeout set it to None
        '''
        dev = self.dev

        # Set oscilloscope into single sequence mode
        # ============================================
        # 1. Stop any current acquisition
        dev.write("ACQ:STATE STOP")
        # 2. Turn on stop after single sequence
        dev.write("ACQ:STOPA SEQ")
        # 3. Acquire data only on one sample
        dev.write("ACQ:MODE SAMPLE")

        print("Starting acquisition")


        # Get the samples
        # ============================================
        dev.write("ACQ:STATE ON")
        
        # Variable for checking timeout
        start_sample = time.time()
        curr_sample = start_sample
        query_no = 1
        state = 1

        # Loop for getting new sample
        while(curr_sample - start_sample < timeout):
            curr_sample = time.time()

            # Check oscilloscope state every 10ms
            if ((curr_sample - start_sample)*100 > query_no): 
                query_no += 1
                state = dev.query("BUSY?")
                # Oscilloscope no longer busy = finished acq
                if int(state) == 0:
                    # Make measurment
                    res = dev.get_waveform(1)
                    return res
        
        # If no signal was caught
        print("FAILED ACQ")
        return None
                