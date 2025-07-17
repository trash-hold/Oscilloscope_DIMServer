from .AbstractInterfaces import Oscilloscope
import socket   # For providing connection to the HTTP server
import numpy as np
from bs4 import BeautifulSoup   # For decoding HTML response


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
            return None
        if self.port is None or isinstance(self.port, int) == False:
            return None
        
        # Connect to the defined socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            s.settimeout(self.timeout) 
            s.connect((self.ip, self.port))
            self.current_connection = s
            return s

        except Exception as e:
            print("CANNOT CONNECT TO THE SOCKET: {0}".format(e.args))
            return None
        
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
        # Open connection
        s = self.connect()
        if s is None:
            print("Failed to read msg. Connection error!")
            return 
        
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


class TDS3054C(Oscilloscope):
    def __init__(self, ip: str = None, port: int = None):
        '''
        Define IPv4 and Port number for future connections.
        '''

        self.curr_socket = None
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
        self.make_connection()

        device_num = self.query("*IDN?")
        print("Connected to: {0}".format(device_num))
        
        if "TDS3054C" in device_num:
            return True
        
        return False

    def set_channel(self, channel: int) -> bool:
        '''
        Validate channel number and set the oscilloscope. Available values are: 1, 2, 3, 4
        '''

        if channel is None:
            print("Tranmission canceled! No channel defined for the write operation")
            return False

        elif channel not in [1, 2, 3, 4]:
            return False

        msg = self.build_msg('DATA:SOURCE CH' + str(channel))
        response = self.socket.send_request(msg)

        return True
    
    def query(self, cmd: str, channel: int = None) -> str:
        '''
        Send data and await response
        '''
        # If channel is None then the command is a general request such as *IDN?
        if channel is not None:
            if self.set_channel(channel) == False:
                print("Transmission canceled: Error during picking the channel!")
                return None

        # Build request contents
        msg = self.build_msg(cmd)
        response = self.socket.send_request(msg)
        
        return self.decode_msg(response)
    
    def write(self, cmd: str, channel: int = None) -> None:
        '''
        Equivalent to set operation, returns nothing 
        '''
        if channel is not None:
            self.set_channel(channel)

        # Build request contents
        msg = self.build_msg(cmd)
        response = self.socket.send_request(msg)

    def configure(self, json_file) -> None:
        print("TBI")

    def get_waveform(self, channel:int, dataformat: str = 'ASCII') -> str: 
        '''
        Reads all data points from current acquisition. Dataformat defines what type of data will be returned by oscilloscope and method.
        
        Available dataformats:
        ASCII -- data is incoming as ASCII characters
        BIN   -- data is coming as signed integers MSB first. One data point is two bytes.
        '''

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
            print(f"ERROR: Could not find response textarea. Raw HTML: {html_bytes.decode(errors='ignore')}")
            return None