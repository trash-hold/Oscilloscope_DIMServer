from enum import Enum

class Command(Enum):
    """
    Defines the command contract between the C++ server and the Python backend.
    
    The member name (e.g., SET_TRIGGER_SLOPE) is used internally in Python.
    The member value (e.g., "set_trigger_slope") is the string sent over ZMQ.
    """
    # Commands originating from the DIM server
    SET_CHANNEL_ENABLED = "set_channel_enabled"
    SET_CHANNEL_SCALE = "set_channel_scale"
    SET_TRIGGER_CHANNEL = "set_trigger_channel"
    SET_TRIGGER_SLOPE = "set_trigger_slope"
    SET_TRIGGER_LEVEL = "set_trigger_level"
    SET_ACQUISITION_MODE = "set_acquisition_mode"
    SET_ACQUISITION_TIMEDIV = "set_acquisition_timediv"
    SET_ACQUISITION_TIMEOUT = "set_acquisition_timeout"
    SET_ACQUISITION_IGNORE = "set_acquisition_ignore"
    RAW_QUERY = "raw_query"
    RAW_WRITE = "raw_write"

class AcquistionMode(Enum):
    CONTINUOUS = "CONT"
    SINGLE = "SINGLE"
    OFF = "OFF"