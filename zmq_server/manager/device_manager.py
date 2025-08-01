import time     # For implementing timeouts
import logging
from zmq_server.common.exceptions import *
from zmq_server.drivers.AbstractInterfaces import Oscilloscope     #Oscilloscope interface class

class DeviceManager():
    def __init__(self, dev:Oscilloscope):
        # Basic handles
        self.dev = dev     # Child of abstract class Oscilloscope

    def start_connection(self) -> None:
        try:
            self.dev.start_connection()
        except DeviceConnectionError as e:
            raise e
    
    def execute_raw_command(self, command: str):
        """
        Executes a raw SCPI command on the device.
        Determines whether to use query() or write() based on the command.
        """
        command = command.strip()
        try:
            if command.endswith('?'):
                response = self.dev.query(command)
                return response.strip()
            else:
                self.dev.write(command)
                return "OK" # Return a simple confirmation for write commands
        except DeviceError as e:
            # Propagate device errors in a structured way
            logging.error(f"Device command '{command}' failed: {e}")
            raise e
        
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
                    print(ch.get('volts_div', 1.0))
                    self.dev.set_vertical_scale(ch_num, ch.get('volts_div', 1.0))
                    self.dev.set_vertical_position(ch_num, ch.get('position', 0.0))

            # --- Apply Horizontal Settings ---
            self.dev.set_horizontal_scale(h_settings.get('time_div', 0.001))
            self.dev.set_horizontal_position(h_settings.get('position', 0.0))

            # --- Apply Trigger Settings ---
            self.dev.set_trigger(
                source=t_settings.get('source', 'CH1'),
                level=t_settings.get('level', 0.0),
                slope=t_settings.get('slope', 'Rising')
            )
            self.dev.set_trigger_level(t_settings.get('source', 'CH1'), t_settings.get('level', 0.0))
            self.dev.set_trigger_slope(t_settings.get('source', 'CH1'), t_settings.get('slope', 'RISE'))
            print("--- [MeasurementManager] Finished Applying Settings ---\n")

        except (DeviceError, ConfigurationError) as e:
            # Re-raise as a configuration error to be caught by the worker
            raise ConfigurationError(f"Failed to apply settings to device: {e}") from e
        
        
    def set_vertical_scale(self, channel_number: int, scale: float) -> None:
        try:
            self.dev.set_vertical_scale(channel_number, scale)
        except DeviceError as e:
            logging.error(f"Device command set_vertical_scale failed: {e}")
            raise e
        
    def set_horizontal_scale(self, scale: float) -> None:
        try:
            self.dev.set_horizontal_scale(scale)
        except DeviceError as e:
            logging.error(f"Device command set_trigger_slope failed: {e}")
            raise e
    
    def get_horizontal_increment(self) -> float:
        try:
            return self.dev.get_horizontal_increment()
        except DeviceError as e:
            logging.error(f"Device command set_trigger_slope failed: {e}")
            raise e
        
    def set_channel_state(self, channel_number: int, state: bool) -> None:
        try:
            self.dev.set_channel_state(channel_number, state)
        except DeviceError as e:
            logging.error(f"Device command set_channel_state failed: {e}")
            raise e
        
    def set_trigger_slope(self, slope: str) -> None:
        try:
            self.dev.set_trigger_slope(slope)
        except DeviceError as e:
            logging.error(f"Device command set_trigger_slope failed: {e}")
            raise e
        
    def set_trigger_level(self, level: float) -> None:
        try:
            self.dev.set_trigger_level(level)
        except DeviceError as e:
            logging.error(f"Device command set_trigger_level failed: {e}")
            raise e
        
    def set_trigger_channel(self, channel: int) -> None:
        try:
            self.dev.set_trigger_channel(channel)
        except DeviceError as e:
            logging.error(f"Device command set_trigger_state failed: {e}")
            raise e
        
    def sample(self, timeout: int) -> None:
        try:
            return self.dev.sample(timeout)
        except DeviceError as e:
            logging.error(f"Device command set_channel_state failed: {e}")
            raise e
        
    def get_waveform(self, channel:int):
        try:
            return self.dev.get_waveform(channel)
        except DeviceError as e:
            logging.error(f"Device command get_waveform failed: {e}")
            raise e
        
    def active_channels(self) -> list:
        try:
            return self.dev.active_channels()
        except DeviceError as e:
            logging.error(f"Device command active_channels failed: {e}")
            raise e