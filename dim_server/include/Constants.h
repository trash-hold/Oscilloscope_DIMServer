#pragma once
#include <string>

namespace Constants {
    // DIM Service Names
    constexpr const char* SERVER_NAME = "OscilloscopeServer";
    constexpr const char* STATE_SERVICE = "SCOPE/STATE";
    constexpr const char* WAVEFORM_SERVICE = "SCOPE/WAVEFORM";
    constexpr const char* REPLY_SERVICE = "SCOPE/REPLY";
    constexpr const char* RAW_COMMAND_SERVICE = "SCOPE/COMMAND";
    // ... add all other DIM command names

    // ZMQ Topics
    constexpr const char* ZMQ_STATE_TOPIC = "backend_state";
    constexpr const char* ZMQ_WAVEFORM_TOPIC = "waveform";

    // JSON Keys
    constexpr const char* JSON_TYPE = "type";
    constexpr const char* JSON_COMMAND = "command";
    constexpr const char* JSON_PARAMS = "params";
    constexpr const char* JSON_ID = "id";
    // ... etc.
}