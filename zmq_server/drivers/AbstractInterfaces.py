from abc import ABC, abstractmethod

class Oscilloscope(ABC):

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
    def set_vertical_scale(self, channel: int, scale: float) -> None:
        """Sets the vertical scale (Volts/Div) for a channel."""
        pass

    @abstractmethod
    def set_vertical_offset(self, channel: int, offset: float) -> None:
        """Sets the vertical offset for a channel."""
        pass

    @abstractmethod
    def set_horizontal_scale(self, scale: float) -> None:
        """Sets the horizontal scale (Seconds/Div)."""
        pass

    @abstractmethod
    def set_horizontal_offset(self, offset: float) -> None:
        """Sets the horizontal offset/position."""
        pass

    @abstractmethod
    def set_trigger(self, source: str, level: float, slope: str) -> None:
        """Sets the main trigger parameters."""
        pass
    
    def get_waveform(self, channel:int) -> str:
        '''
        Acquisition of registered waveform
        '''
        pass

