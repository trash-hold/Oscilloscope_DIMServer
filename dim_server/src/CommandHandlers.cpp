#include "CommandHandlers.h"
#include "ZMQCommunicator.h"
#include "DimServices.h"
#include "Constants.h"

using json = nlohmann::json;

FlexibleJsonCommand::FlexibleJsonCommand(ZmqCommunicator& comm, const char* dim_name, const char* dim_format,
                                         std::string py_cmd, ParamPopulator param_populator) :
    DimCommand(dim_name, dim_format),
    zmq_comm(comm),
    python_command(std::move(py_cmd)),
    populator(std::move(param_populator))
{}

void FlexibleJsonCommand::commandHandler() {
    json j;
    j[Constants::JSON_ID] = python_command + "_" + std::to_string(command_counter++);
    j[Constants::JSON_COMMAND] = python_command;

    populator(this, j[Constants::JSON_PARAMS]);

    zmq_comm.send_command(j.dump());
}


RawCommandService::RawCommandService(ZmqCommunicator& comm) :
    DimCommand(Constants::RAW_CMD, "C"), zmq_comm(comm) {}

void RawCommandService::commandHandler() {
    std::string cmd_text = getString();
    json j;
    j[Constants::JSON_ID] = "raw_cmd_" + std::to_string(command_counter++);
    j[Constants::JSON_TYPE] = "command";
    if (cmd_text.find('?') != std::string::npos) {
        j[Constants::JSON_COMMAND] = Constants::PY_RAW_QUERY;
        j[Constants::JSON_PARAMS] = { {Constants::JSON_QUERY, cmd_text} };
    } else {
        j[Constants::JSON_COMMAND] = Constants::PY_RAW_WRITE;
        j[Constants::JSON_PARAMS] = { {Constants::JSON_COMMAND, cmd_text} };
    }
    zmq_comm.send_command(j.dump());
}