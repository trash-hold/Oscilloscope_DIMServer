#include "CommandRegistry.h"
#include "CommandHandlers.h"
#include "ZMQCommunicator.h"
#include "Constants.h"

using json = nlohmann::json;

void register_all_commands(ZmqCommunicator& comm) {

    // --- Register Generic Commands using Lambdas ---
    // SCOPE/TRIGGER/SET_CHANNEL (String parameter)
    new FlexibleJsonCommand(comm, Constants::TRIG_SET_CHANNEL_CMD, "I", Constants::PY_SET_TRIG_CHANNEL,
        [](DimCommand* cmd, json& params) {
            params["channel"] = cmd->getInt();
        }
    );
    // SCOPE/TRIGGER/SET_SLOPE (String parameter)
    new FlexibleJsonCommand(comm, Constants::TRIG_SET_SLOPE_CMD, "C", Constants::PY_SET_TRIG_SLOPE,
        [](DimCommand* cmd, json& params) {
            params["slope"] = cmd->getString();
        }
    );

    // SCOPE/TRIGGER/SET_LEVEL (Float parameter)
    new FlexibleJsonCommand(comm, Constants::TRIG_SET_LEVEL_CMD, "F", Constants::PY_SET_TRIG_LEVEL,
        [](DimCommand* cmd, json& params) {
            params["level"] = cmd->getFloat();
        }
    );

    // SCOPE/ACQUISITION/SET_TIMEDIV (Float parameter)
    new FlexibleJsonCommand(comm, Constants::ACQ_SET_TIMEDIV_CMD, "F", Constants::PY_SET_ACQ_TIMEDIV,
        [](DimCommand* cmd, json& params) {
            params["level"] = cmd->getFloat();
        }
    );

    // SCOPE/ACQUISITION/SET_TIMEOUT (Float parameter)
    new FlexibleJsonCommand(comm, Constants::ACQ_SET_TIMEOUT_CMD, "F", Constants::PY_SET_ACQ_TIMEOUT,
        [](DimCommand* cmd, json& params) {
            params["level"] = cmd->getFloat();
        }
    );

    // SCOPE/ACQUISITION/IGNORE_TIMEOUT (Char parameter -- interpreted as bool)
    new FlexibleJsonCommand(comm, Constants::ACQ_SET_IGNORE_CMD, "C", Constants::PY_SET_ACQ_IGNORE,
        [](DimCommand* cmd, json& params) {
            params["state"] = cmd->getString();
        }
    );

    // SCOPE/ACQUISITION/SET_STATE (String parameter)
    new FlexibleJsonCommand(comm, Constants::ACQ_SET_MODE_CMD, "C", Constants::PY_SET_ACQ_MODE,
        [](DimCommand* cmd, json& params) {
            params["state"] = cmd->getString();
        }
    );


    // --- Register Channel Commands using Lambdas ---

    // SCOPE/CHANNEL/SET_ENABLED (Channel + Value parameter)
    new FlexibleJsonCommand(comm, Constants::CHAN_SET_ENABLED_CMD, "I:1;F:1", Constants::PY_SET_CHAN_ENABLED,
        [](DimCommand* cmd, json& params) {
            auto* data = static_cast<ChannelCommandData*>(cmd->getData());
            params[Constants::JSON_CHANNEL] = data->channel;
            params["enabled"] = (data->value != 0.0f); // Convert float to boolean for clarity
        }
    );

    // SCOPE/CHANNEL/SET_SCALE (Channel + Value parameter)
    new FlexibleJsonCommand(comm, Constants::CHAN_SET_SCALE_CMD, "I:1;F:1", Constants::PY_SET_CHAN_SCALE,
        [](DimCommand* cmd, json& params) {
            auto* data = static_cast<ChannelCommandData*>(cmd->getData());
            params[Constants::JSON_CHANNEL] = data->channel;
            params["scale"] = data->value;
        }
    );


    // --- Register Specialized Commands ---
    new RawCommandService(comm);
}