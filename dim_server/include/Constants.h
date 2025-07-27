namespace Constants {
    // DIM Server and Service Names
    constexpr const char* SERVER_NAME = "OscilloscopeServer";
    constexpr const char* REPLY_SERVICE = "SCOPE/REPLY";
    constexpr const char* STATE_SERVICE = "SCOPE/STATE";
    constexpr const char* WAVEFORM_SERVICE = "SCOPE/WAVEFORM";

    // COMMAND NAMES 
    constexpr const char* RAW_CMD = "SCOPE/RAW";
    constexpr const char* CHAN_SET_ENABLED_CMD = "SCOPE/CHANNEL/SET_ENABLED";
    constexpr const char* CHAN_SET_SCALE_CMD = "SCOPE/CHANNEL/SET_SCALE";
    constexpr const char* TRIG_SET_CHANNEL_CMD = "SCOPE/TRIGGER/SET_CHANNEL";
    constexpr const char* TRIG_SET_SLOPE_CMD = "SCOPE/TRIGGER/SET_SLOPE";
    constexpr const char* TRIG_SET_LEVEL_CMD = "SCOPE/TRIGGER/SET_LEVEL";
    constexpr const char* ACQ_SET_STATE_CMD = "SCOPE/ACQUISITION/SET_STATE";

    // ZMQ Endpoints and Topics
    constexpr const char* ZMQ_ROUTER_ENDPOINT = "tcp://*:5555";
    // This MUST match the 'dim_publish_endpoint' in the Python config
    constexpr const char* ZMQ_SUB_ENDPOINT = "tcp://localhost:5558"; 
    constexpr const char* ZMQ_STATE_TOPIC = "backend_state";
    constexpr const char* ZMQ_WAVEFORM_TOPIC = "waveform";

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
    constexpr const char* PY_SET_ACQ_STATE = "set_acquisition_state";
    constexpr const char* PY_RAW_QUERY = "raw_query";
    constexpr const char* PY_RAW_WRITE = "raw_write";
}