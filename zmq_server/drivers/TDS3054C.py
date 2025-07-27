from .AbstractInterfaces import Oscilloscope
import time 
from enum import Enum
import socket   # For providing connection to the HTTP server
import numpy as np
from bs4 import BeautifulSoup   # For decoding HTML response
from common.exepction import * 

class Slope(Enum):
    RISING = "RISE"
    FALLING = "FALL"

class EthernetSocket():
    '''
    Class that takes care of sending and reading HTTP requests.
    '''

    def __init__(self, ip: str = None, port: int = None):
        self.ip = ip
        self.port = port
        self.timeout = 15
        self.current_connection = None
    
    def connect(self) -> socket.socket:
        '''
        Opens socket and returns it. Returns None on failure
        '''
        # Check if socket was well defined
        if self.ip is None:
            raise DeviceConnectionError("FATAL ERROR: Haven't provided IP")
        if self.port is None or isinstance(self.port, int) == False:
            raise DeviceConnectionError("FATAL ERROR: Haven't provided PORT")
        
        # Connect to the defined socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            s.settimeout(self.timeout) 
            s.connect((self.ip, self.port))
            self.current_connection = s
            return s

        except (socket.timeout, OSError) as e:
            raise DeviceConnectionError(f"Cannot connect to device at {self.ip}:{self.port}") from e
        
    def close(self):
        '''
        Closes connection if it's open
        '''
        if self.current_connection is not None:
            self.current_connection.close()
            self.current_connection = None


    def timeout(self, time: int):
        '''
        Changes timeout time for socket operations
        '''
        self.timeout = time

    def send_request(self, req_bytes: str) -> bytes:
        '''
        Opens connection, sends request and returns byte response
        '''
        try:
            # Open connection
            s = self.connect()
            
            # Send bytes
            s.sendall(req_bytes)
            
            # Read response
            full_response_bytes = b''
            while True:
                chunk = s.recv(8192) # Larger buffer in case of waveform data
                if not chunk:
                    break
                full_response_bytes += chunk


            self.close()
            return full_response_bytes
        except (DeviceConnectionError, socket.timeout, OSError) as e:
            self.close()
            raise DeviceCommunicationError("Failed to send or receive data from device.") from e



class TDS3054C(Oscilloscope):
    def __init__(self, connection_params: dict):
        '''
        Define IPv4 and Port number for future connections.
        '''

        ip = connection_params.get('ip')
        port = connection_params.get('port')
        self.socket = EthernetSocket(ip, port)


    def make_connection(self):
        '''
        WARNING! In this specific application the socket port ought to be opened and closed with each command. This is due to the buggy web interface provided by the manufactur.
        '''
        self.socket.connect()


    def end_connection(self) -> None:
        '''
        WARNING! Connection is automatically closed in the methods inside this class
        '''
        self.socket.close()


    def test_connection(self) -> bool:
        '''
        Checks if the connection can be established and if the device is TDS3054C 
        '''
        try:
            self.make_connection()

            device_num = self.query("*IDN?")
            print("Connected to: {0}".format(device_num))
            
            if "TDS 3054C" in device_num:
                return True
            
            raise UnexpectedDeviceError(f"The connected device identifies as '{device_num}', not TDS3054C.")
        
        except DeviceError as e:
            raise DeviceCommandError("Failed during test connection.") from e


    def set_channel(self, channel: int) -> None:
        '''
        Validate channel number and set the oscilloscope. Available values are: 1, 2, 3, 4
        '''

        if channel is None:
            raise InvalidParameterError("Error! Haven't set the channel number for the operation")

        elif channel not in [1, 2, 3, 4]:
            raise InvalidParameterError(f"Error! Channel number should be in range 1-2, given {channel}")

        try:
            msg = self.build_msg('DATA:SOURCE CH' + str(channel))
            self.socket.send_request(msg)

        except DeviceCommunicationError as e:
            raise DeviceCommandError(f"Failed to set channel to {channel}.") from e
    

    def query(self, cmd: str, channel: int = None) -> str:
        '''
        Send data and await response
        '''
        # If channel is None then the command is a general request such as *IDN?
        
        try:
            if channel is not None:
                self.set_channel(channel)


            # Build request contents
            msg = self.build_msg(cmd)
            response = self.socket.send_request(msg)
            
            return self.decode_msg(response)
    
        except (DeviceCommunicationError, InvalidParameterError, ParsingError) as e:
            raise DeviceCommandError(f"Query command '{cmd}' failed.") from e
    

    def write(self, cmd: str, channel: int = None) -> None:
        '''
        Equivalent to set operation, returns nothing 
        '''
        try:
            if channel is not None:
                self.set_channel(channel)

            # Build request contents
            msg = self.build_msg(cmd)
            response = self.socket.send_request(msg)

        except (DeviceCommunicationError, InvalidParameterError) as e:
            raise DeviceCommandError(f"Write command '{cmd}' failed.") from e
        
    
    def set_channel_state(self, channel: int, enabled: bool) -> None:
        try:
            state = "ON" if enabled else "OFF"
            command = f"SELECT:CH{channel} {state}"
            self.write(command)
            print(f"[TDS3054C] Executed: {command}")
        except DeviceCommandError as e:
            raise DeviceCommandError(f"Failed to set state for channel {channel}.") from e


    def set_vertical_scale(self, channel: int, scale: float) -> None:
        try:
            command = f"CH{channel}:SCAle {scale:.4E}"
            self.write(command)
            print(f"[TDS3054C] Executed: {command}")
        except DeviceCommandError as e:
            raise DeviceCommandError(f"Failed to set vertical scale for channel {channel}.") from e
        

    def set_vertical_position(self, channel: int, offset: float) -> None:
        try:
            command = f"CH{channel}:POSition {offset:g}"
            self.write(command)
            print(f"[TDS3054C] Executed: {command}")
        except DeviceCommandError as e:
            raise DeviceCommandError(f"Failed to set vertical offset for channel {channel}.") from e


    def set_horizontal_scale(self, scale: float) -> None:
        try:
            command = f"HORizontal:MAIn:SCAle {scale:g}"
            self.write(command)
            print(f"[TDS3054C] Executed: {command}")
        except DeviceCommandError as e:
            raise DeviceCommandError("Failed to set horizontal scale.") from e


    def set_horizontal_position(self, offset: float) -> None:
        try:
            command = f"HORizontal:MAIn:POSition {offset:g}"
            self.write(command)
            print(f"[TDS3054C] Executed: {command}")
        except DeviceCommandError as e:
            raise DeviceCommandError("Failed to set horizontal offset.") from e

    def set_trigger_level(self, channel: int, level: float) -> None:
        try:
            level_command = f"TRIGger:A:LEVel {level:g}"
            self.write(level_command)
            print(f"[TDS3054C] Executed: {level_command}")
        except DeviceCommandError as e:
            raise DeviceCommandError("Failed to configure trigger settings.") from e
    
    def set_trigger_slope(self, slope: str) -> None:
        try:
            if slope == Slope.FALLING.value or slope == Slope.RISING.value:
                slope_command = f"TRIGger:A:EDGE:SLOpe {slope}"
                self.write(slope_command)
                print(f"[TDS3054C] Executed: {slope_command}")
            else:
                raise DeviceCommandError("Failed to set the edge to: {slope}, check the driver's Slope classs")
        except DeviceCommandError as e:
            raise DeviceCommandError("Failed to configure trigger settings.") from e
        
    def set_trigger_channel(self, channel: int) -> None:
        try:
            if channel not in [1, 2, 3, 4]:
                raise DeviceCommandError("Faile to change trigger channel to {channel} -- out of bounds")
            source_command = f"TRIGger:A:EDGE:SOUrce CH{channel}"
            self.write(source_command)
            print(f"[TDS3054C] Executed: {source_command}")

        except DeviceCommandError as e:
            raise DeviceCommandError("Failed to configure trigger settings.") from e
        

    def get_waveform(self, channel:int, dataformat: str = 'ASCII') -> str: 
        '''
        Reads all data points from current acquisition. Dataformat defines what type of data will be returned by oscilloscope and method.
        
        Available dataformats:
        ASCII -- data is incoming as ASCII characters
        BIN   -- data is coming as signed integers MSB first. One data point is two bytes.
        '''
        try:
            if self.set_channel(channel) == False:
                return None
            
            # Set encoding
            if dataformat == 'ASCII':
                self.write('DATA:ENCDG ASCII')
            elif dataformat == 'BIN':
                self.write('DATA:ENCDG RIB')
                self.write('DATA:WID 2')
            else:
                print("Transmission canceled! Incorrect dataformat: {0}".format(dataformat))

            # These values are needed to convert raw ADC levels to Volts
            ymult_str = self.query('WFMPRE:YMULT?')
            yzero_str = self.query('WFMPRE:YZERO?')
            yoff_str = self.query('WFMPRE:YOFF?')

            ymult = float(ymult_str)
            yzero = float(yzero_str)
            yoff = float(yoff_str)

            print("TBI time step")

            # Acquire the data points
            raw_data = self.query('CURVE?')

            true_waveform = []
            # Process the data
            if dataformat == 'ASCII':
                raw_points = [int(p) for p in raw_data.split(',')]
        
                # Apply the scaling formula t
                true_waveform = [(point - yoff) * ymult + yzero for point in raw_points]

            elif dataformat == 'BIN':
                print("TBI")
                return None

            if true_waveform is not None:
                return np.array(true_waveform, dtype=np.float64)
            else:
                return None
        
        except (DeviceCommandError, ValueError) as e:
            raise DeviceCommandError(f"Failed to get waveform from channel {channel}.") from e
        
    def sample(self, timeout: int = 60) -> np.array:
        '''
        Runs oscilloscope in single sequence mode and waits for a single acquistion -- has timeout feature. If you want to turn off the timeout set it to None
        '''
        try:

            # Set oscilloscope into single sequence mode
            # ============================================
            # 1. Stop any current acquisition
            self.write("ACQ:STATE STOP")
            # 2. Turn on stop after single sequence
            self.write("ACQ:STOPA SEQ")
            # 3. Acquire data only on one sample
            self.write("ACQ:MODE SAMPLE")

            print("Starting acquisition")


            # Get the samples
            # ============================================
            self.write("ACQ:STATE ON")
            
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
                    state = self.query("BUSY?")
                    # Oscilloscope no longer busy = finished acq
                    if int(state) == 0:
                        # Make measurment
                        res = self.get_waveform(1)
                        return res
            
            # If no signal was caught
            raise AcquisitionTimeoutError(f"Acquisition timed out after {timeout} seconds.")
        
        except (DeviceCommandError, ValueError) as e:
            raise AcquisitionError("A device error occurred during the acquisition sequence.") from e
        


    def build_msg(self, command: str) -> str:
        '''
        Builds HTTP request body message according to the oscilloscope needs. Check ""
        '''
        body = f"COMMAND={command}&gpibsend=Send"
        body_bytes = body.encode('utf-8')
        
        headers = [
            "POST /Comm.html HTTP/1.1",
            f"Host: {self.socket.ip}",
            "Content-Type: application/x-www-form-urlencoded",
            f"Content-Length: {len(body_bytes)}",
            "Connection: close",
        ]
        request_str = "\r\n".join(headers) + "\r\n\r\n"
        request_bytes = request_str.encode('utf-8') + body_bytes

        return request_bytes
    

    def decode_msg(self, msg: str) -> str:
        '''
        Decodes the incoming HTML data. If the textarea fied is not found returns None.
        '''
        header_end_pos = msg.find(b'\r\n\r\n')
        html_bytes = msg[header_end_pos + 4:] if header_end_pos != -1 else msg
        
        soup = BeautifulSoup(html_bytes, 'html.parser')
        response_textarea = soup.find('textarea', {'name': 'name'})
        
        if response_textarea:
            return response_textarea.get_text(strip=True)
        else:
            # If parsing fails, return the raw HTML for debugging
            print(f"Raw HTML: {html_bytes.decode(errors='ignore')}")
            raise ParsingError("Could not find response textarea in device's HTML response.")