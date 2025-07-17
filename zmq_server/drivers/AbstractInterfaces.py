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
    def configure(self, json_file: str) -> None:
        '''
        Implement oscilloscope configuration by the settings saved in json_file
        '''
        pass
    
    def get_waveform(self, channel:int) -> str:
        '''
        Acquisition of registered waveform
        '''
        pass

