
from drivers.AbstractInterfaces import Oscilloscope     #Oscilloscope interface class
import json     # For reading config files
import time     # For implementing timeouts
from common.exepction import *

class MeasurementManager():
    def __init__(self, dev:Oscilloscope, json_file:str = None):
        # Basic handles
        self.dev = dev     # Child of abstract class Oscilloscope
        self.config = self.load_config(json_file) if json_file is not None else None

    def start_connection(self) -> None:
        try:
            self.dev.start_connection()
        except DeviceConnectionError as e:
            raise e

    def load_config(self, json_file: str) -> dict:
        '''
        Connect and configure the oscilloscope according to the defined json file.
        '''
        try: 
            # Load the file
            config = None
            with open(json_file, 'r') as file:
                config = json.load(file)
                file.close()

            # Connect to device
            if self.dev is None:
                raise ConfigurationError("Device handle has not been provided to the manager.")
            
            self.dev.test_connection() 

            self.dev.config(json_file)
            self.config = config

            print("Successfully configured the oscilloscope!")
            return config
        
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ConfigurationError(f"Failed to load or parse config file: {json_file}") from e
        
        except DeviceError as e:
            raise ConfigurationError("Failed to configure the device. Check connection and config values.") from e
    
    def apply_settings(self, settings: dict):
        """
        Applies new measurement settings to the device.
        Currently a MOCK function that prints intended actions.
        """
        print("\n--- [MeasurementManager] Applying New Settings ---")
        
        # Use .get() to safely access dictionary keys
        ch_settings = settings.get('channels', [])
        h_settings = settings.get('horizontal', {})
        t_settings = settings.get('trigger', {})

        self._apply_channel_settings(ch_settings)
        self._apply_horizontal_settings(h_settings)
        self._apply_trigger_settings(t_settings)

        print("--- [MeasurementManager] Finished Applying Settings ---\n")

    def _apply_channel_settings(self, ch_settings: list):
        """Mock function to apply channel settings."""
        print("[MOCK] Applying Channel Settings:")
        for i, ch in enumerate(ch_settings):
            if ch.get('enabled'):
                print(f"  - CH{i+1}: ON | Volts/Div: {ch.get('volts_div')} | Offset: {ch.get('offset'):.3f} V")
            else:
                print(f"  - CH{i+1}: OFF")
    
    def _apply_horizontal_settings(self, h_settings: dict):
        """Mock function to apply horizontal settings."""
        print("[MOCK] Applying Horizontal Settings:")
        print(f"  - Time/Div: {h_settings.get('time_div')} | Offset: {h_settings.get('offset'):.3f} s")

    def _apply_trigger_settings(self, t_settings: dict):
        """Mock function to apply trigger settings."""
        print("[MOCK] Applying Trigger Settings:")
        print(f"  - Source: {t_settings.get('source')} | Level: {t_settings.get('level'):.3f} V | Slope: {t_settings.get('slope')}")
    
    def sample(self, timeout: int = 60) -> None:
        '''
        Runs oscilloscope in single sequence mode and waits for a single acquistion -- has timeout feature. If you want to turn off the timeout set it to None
        '''
        try:
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
            raise AcquisitionTimeoutError(f"Acquisition timed out after {timeout} seconds.")
        
        except (DeviceCommandError, ValueError) as e:
            raise AcquisitionError("A device error occurred during the acquisition sequence.") from e
                