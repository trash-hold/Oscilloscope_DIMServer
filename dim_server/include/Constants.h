#include <string>

namespace Constants {
    // DIM Server and Service Names
    constexpr const char* SERVER_NAME = "OscilloscopeServer";
    constexpr const char* REPLY_SERVICE = "SCOPE/REPLY";
    constexpr const char* STATE_SERVICE = "SCOPE/STATE";
    constexpr const char* TIMEDIV_SERVICE = "SCOPE/TIME_INCREMENT";
    const std::string WAVEFORM_SERVICE_BASE = "SCOPE/ACQUISITION/CH";

    // COMMAND NAMES 
    constexpr const char* RAW_CMD = "SCOPE/RAW";
    constexpr const char* CHAN_SET_ENABLED_CMD = "SCOPE/CHANNEL/SET_ENABLED";
    constexpr const char* CHAN_SET_SCALE_CMD = "SCOPE/CHANNEL/SET_SCALE";
    constexpr const char* TRIG_SET_CHANNEL_CMD = "SCOPE/TRIGGER/SET_CHANNEL";
    constexpr const char* TRIG_SET_SLOPE_CMD = "SCOPE/TRIGGER/SET_SLOPE";
    constexpr const char* TRIG_SET_LEVEL_CMD = "SCOPE/TRIGGER/SET_LEVEL";
    constexpr const char* ACQ_SET_TIMEDIV_CMD = "SCOPE/ACQUISITION/SET_TIMEDIV";
    constexpr const char* ACQ_SET_TIMEOUT_CMD = "SCOPE/ACQUISITION/SET_TIMEOUT";
    constexpr const char* ACQ_SET_IGNORE_CMD = "SCOPE/ACQUISITION/IGNORE_TIMEOUT";
    constexpr const char* ACQ_SET_MODE_CMD = "SCOPE/ACQUISITION/SET_MODE";

    // ZMQ Endpoints and Topics
    constexpr const char* ZMQ_ROUTER_ENDPOINT = "tcp://*:5555";
    // This MUST match the 'dim_publish_endpoint' in the Python config
    constexpr const char* ZMQ_SUB_ENDPOINT = "tcp://localhost:5558"; 
    constexpr const char* ZMQ_STATE_TOPIC = "backend_state";
    constexpr const char* ZMQ_TIMEDIV_TOPIC = "waveform_timediv";
    const std::string ZMQ_WAVEFORM_TOPIC_BASE = "waveform_ch";

    // JSON Keys
    constexpr const char* JSON_TYPE = "type";
    constexpr const char* JSON_ID = "id";
    constexpr const char* JSON_COMMAND = "command";
    constexpr const char* JSON_PARAMS = "params";
    constexpr const char* JSON_STATUS = "status";
    constexpr const char* JSON_PAYLOAD = "payload";
    constexpr const char* JSON_MESSAGE = "message";
    constexpr const char* JSON_QUERY = "query";
    constexpr const char* JSON_CHANNEL = "channel";

    // Python Command Names ---
    constexpr const char* PY_SET_CHAN_ENABLED = "set_channel_enabled";
    constexpr const char* PY_SET_CHAN_SCALE = "set_channel_scale";
    constexpr const char* PY_SET_TRIG_CHANNEL = "set_trigger_channel";
    constexpr const char* PY_SET_TRIG_SLOPE = "set_trigger_slope";
    constexpr const char* PY_SET_TRIG_LEVEL = "set_trigger_level";
    constexpr const char* PY_SET_ACQ_MODE = "set_acquisition_mode";
    constexpr const char* PY_SET_ACQ_TIMEDIV = "set_acquisition_timediv";
    constexpr const char* PY_SET_ACQ_TIMEOUT = "set_acquisition_timeout";
    constexpr const char* PY_SET_ACQ_IGNORE = "set_acquisition_ignore";
    constexpr const char* PY_RAW_QUERY = "raw_query";
    constexpr const char* PY_RAW_WRITE = "raw_write";

    // App specific
    const int OSC_NUM_CHANNELS = 4;   
    const int WAVEFORM_BUFFER_SIZE = 130000; 
    const int STATE_BUFFER_SIZE = 256; 
}