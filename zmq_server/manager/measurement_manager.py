
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
        Applies new measurement settings to the device by calling the
        high-level abstract methods of the driver.
        """
        print("\n--- [MeasurementManager] Applying New Settings to Driver ---")
        
        ch_settings = settings.get('channels', [])
        h_settings = settings.get('horizontal', {})
        t_settings = settings.get('trigger', {})

        try:
            # --- Apply Channel Settings ---
            for i, ch in enumerate(ch_settings):
                ch_num = i + 1
                self.dev.set_channel_state(ch_num, ch.get('enabled', False))
                if ch.get('enabled'):
                    scale = self._parse_value_with_unit(ch.get('volts_div', '1'))
                    self.dev.set_vertical_scale(ch_num, scale)
                    self.dev.set_vertical_offset(ch_num, ch.get('offset', 0.0))

            # --- Apply Horizontal Settings ---
            h_scale = self._parse_value_with_unit(h_settings.get('time_div', '1ms'))
            self.dev.set_horizontal_scale(h_scale)
            self.dev.set_horizontal_offset(h_settings.get('offset', 0.0))

            # --- Apply Trigger Settings ---
            self.dev.set_trigger(
                source=t_settings.get('source', 'CH1'),
                level=t_settings.get('level', 0.0),
                slope=t_settings.get('slope', 'Rising')
            )
            print("--- [MeasurementManager] Finished Applying Settings ---\n")

        except (DeviceError, ConfigurationError) as e:
            # Re-raise as a configuration error to be caught by the worker
            raise ConfigurationError(f"Failed to apply settings to device: {e}") from e
        
    def _parse_value_with_unit(self, value_str: str) -> float:
        """
        Parses a string like "500mV" or "10us" into a float in base units (V or s).
        """
        value_str = value_str.strip().lower()
        try:
            if 'mv' in value_str:
                return float(value_str.replace('mv', '')) * 1e-3
            if 'v' in value_str:
                return float(value_str.replace('v', ''))
            if 'ms' in value_str:
                return float(value_str.replace('ms', '')) * 1e-3
            if 'us' in value_str:
                return float(value_str.replace('us', '')) * 1e-6
            if 's' in value_str:
                return float(value_str.replace('s', ''))
            # Default case if no unit found
            return float(value_str)
        except (ValueError, TypeError):
            raise ConfigurationError(f"Could not parse value: '{value_str}'")
    
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
                