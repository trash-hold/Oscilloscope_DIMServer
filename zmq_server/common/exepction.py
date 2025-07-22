
#====================================================================================
# Device Errors 
#====================================================================================

class DeviceError(Exception):
    """Base exception for all device-related errors."""
    def __init__(self, message="A device error occurred.", device_id=None, **kwargs):
        self.message = message
        # Store any other relevant context
        self.context = kwargs
        super().__init__(self.message)

    def to_dict(self):
        """Serializes the exception data to a dictionary for transport."""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'context': self.context
        }
    
class DeviceConnectionError(DeviceError):
    """For errors during the connection phase (socket connect, IP/port config)."""
    pass

class DeviceCommunicationError(DeviceError):
    """For errors after connection (send/recv failures, timeouts)."""
    pass

class UnexpectedDeviceError(DeviceError):
    """For when the connected device is not the expected model."""
    pass

class InvalidParameterError(DeviceError):
    """For when a bad parameter (e.g., channel number) is provided."""
    pass

class DeviceCommandError(DeviceError):
    """A wrapper for errors that occur during a query/write operation."""
    pass

class ParsingError(DeviceError):
    """For errors when decoding or parsing a response from the device."""
    pass

class ConfigurationError(DeviceError):
    """Raised when a device cannot be configured correctly from a file."""
    pass

#====================================================================================
# Acquisition Errors 
#====================================================================================
class AcquisitionError(DeviceError):
    """A general error during a data acquisition sequence."""
    pass

class AcquisitionTimeoutError(AcquisitionError): # Note: It inherits from AcquisitionError
    """Raised specifically when an acquisition times out waiting for a trigger."""
    pass

#====================================================================================
# ZMQ Server errors
#====================================================================================
class ZMQCommunicationError(DeviceError):
    """A base class for errors during ZMQ communication."""
    pass

class ZMQTimeoutError(ZMQCommunicationError):
    """Raised when a ZMQ socket poll times out waiting for a reply."""
    pass