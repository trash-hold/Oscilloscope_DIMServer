from abc import ABC, abstractmethod
from enum import Enum

class Oscilloscope(ABC):

    @abstractmethod
    def __init__(self, connection_params: dict):
        """
        Initializes the driver with device-specific connection parameters.
        """
        pass
    
    @abstractmethod 
    def make_connection(self) -> None:
        '''
        Used to connect with the device. Should be called before running other commands.
        '''
        pass

    @abstractmethod
    def end_connection(self) -> None:
        '''
        Used to end the connection with the device safely. Should be called as the last command.
        '''
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        '''
        Implement *IDN? query to validate if the device responds correctly
        '''

    @abstractmethod
    def query(self, cmd:str, channel:int) -> str:
        '''
        Used to send r / rw command to the oscilloscope
        '''
        pass

    @abstractmethod
    def write(self, cmd:str, channel:int) -> None:
        '''
        Used to set registers/parameters in the oscilloscope. No return values.
        '''
        pass

    @abstractmethod
    def set_channel(self, channel:int) ->  bool:
        '''
        Changes the channel used for the measurments/operations
        '''
        pass

    @abstractmethod
    def active_channels(self) ->  list:
        '''
        Returns all enabled channels
        '''
        pass

    @abstractmethod
    def set_vertical_scale(self, channel: int, scale: float) -> None:
        """Sets the vertical scale (Volts/Div) for a channel."""
        pass

    @abstractmethod
    def set_vertical_position(self, channel: int, offset: float) -> None:
        """Sets the vertical offset for a channel."""
        pass

    @abstractmethod
    def set_horizontal_scale(self, scale: float) -> None:
        """Sets the horizontal scale (Seconds/Div)."""
        pass

    @abstractmethod
    def set_horizontal_position(self, offset: float) -> None:
        """Sets the horizontal offset/position."""
        pass

    @abstractmethod
    def get_horizontal_increment(self) -> float:
        """Read the horizontal increment"""
        pass

    @abstractmethod
    def set_trigger_level(self, level: float) -> None:
        """Sets the trigger level"""
        pass

    @abstractmethod
    def set_trigger_slope(self, slope: str) -> None:
        """"Sets the trigger slope"""
        pass

    @abstractmethod
    def set_trigger_channel(self, channel: int) -> None:
        """"Sets the trigger source"""
        pass
    
    def get_waveform(self, channel:int) -> str:
        '''
        Acquisition of registered waveform
        '''
        pass

    def sample(self, timeout: int = 60):
            '''
            Runs oscilloscope in single sequence mode and waits for a single acquistion -- optional implementation of timeout feature
            '''
            pass

