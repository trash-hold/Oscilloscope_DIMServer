#pragma once

#include <dis.hxx>
#include <string>
#include <functional>
#include <nlohmann/json.hpp>

class ZmqCommunicator; // Forward declaration

// A highly flexible command handler that uses a lambda to populate parameters.
class FlexibleJsonCommand : public DimCommand {
    using json = nlohmann::json;
    // A function that takes a pointer to the command itself and a reference to the JSON object to be filled.
    using ParamPopulator = std::function<void(DimCommand*, json&)>;

    ZmqCommunicator& zmq_comm;
    std::string python_command;
    ParamPopulator populator; // Stores the lambda
    long command_counter = 0;

public:
    FlexibleJsonCommand(ZmqCommunicator& comm, const char* dim_name, const char* dim_format,
                        std::string py_cmd, ParamPopulator param_populator);

    void commandHandler() override;
};

// We still need the struct for multi-parameter commands.
struct ChannelCommandData {
    int channel;
    float value;
};

// RawCommandService is specialized and remains as is.
class RawCommandService : public DimCommand {
    ZmqCommunicator& zmq_comm;
    long command_counter = 0;
public:
    RawCommandService(ZmqCommunicator& comm);
    void commandHandler() override;
};