#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <chrono>

#include <dis.hxx>
#include <zmq.hpp>
#include <zmq_addon.hpp>
#include <nlohmann/json.hpp>

// for convenience
using json = nlohmann::json;

// Forward declaration
class ZmqCommunicator;

// ===================================================================
// Service to hold the reply from the oscilloscope
// ===================================================================
class ReplyService {
    char buffer[2048];
    DimService reply_service;
    std::mutex mtx;

public:
    ReplyService() :
        reply_service("SCOPE/REPLY", buffer)
    {
        // Initialize the buffer to a known state.
        buffer[0] = '\0';
    }

    void update(const std::string& new_reply) {
        std::lock_guard<std::mutex> lock(mtx);

        strncpy(buffer, new_reply.c_str(), sizeof(buffer));
        buffer[sizeof(buffer) - 1] = '\0';
        reply_service.updateService();

        std::cout << "Updated SCOPE/REPLY with: " << buffer << std::endl;
    }
};


// ===================================================================
// Command service to receive commands from DIM clients
// ===================================================================
class CommandService : public DimCommand {
    ZmqCommunicator& zmq_comm;
    long command_counter;

public:
    CommandService(ZmqCommunicator& comm);
    void commandHandler() override;
};


// ===================================================================
// Handles asynchronous ZMQ communication in a separate thread
// ===================================================================
class ZmqCommunicator {
    zmq::context_t context;
    std::mutex client_id_mutex;

    std::atomic<bool> running;
    
    zmq::message_t python_client_id;

    zmq::socket_t router_socket;
    zmq::socket_t sub_socket;

    std::thread router_thread;
    std::thread sub_thread; 

    ReplyService& reply_svc;
    DimService state_svc;
    DimService waveform_svc;

    char state_buffer[256];
    char waveform_buffer[32768]; // Waveforms can be large




public:
    ZmqCommunicator(ReplyService& service) :
        context(1),
        running(false),
        router_socket(context, zmq::socket_type::router),
        sub_socket(context, zmq::socket_type::sub),
        reply_svc(service),
        state_svc("SCOPE/STATE", state_buffer),
        waveform_svc("SCOPE/WAVEFORM", waveform_buffer)
    {
        state_buffer[0] = '\0';
        waveform_buffer[0] = '\0';
    }

    ~ZmqCommunicator() {
        stop();
    }

    void start(const std::string& router_endpoint, const std::string& sub_endpoint) {
        router_socket.bind(router_endpoint);
        sub_socket.connect(sub_endpoint);
        sub_socket.set(zmq::sockopt::subscribe, "backend_state");
        sub_socket.set(zmq::sockopt::subscribe, "waveform");

        running = true;
        router_thread = std::thread(&ZmqCommunicator::router_loop, this);
        sub_thread = std::thread(&ZmqCommunicator::subscribe_loop, this);
        std::cout << "ZMQ ROUTER listening on " << router_endpoint << std::endl;
        std::cout << "ZMQ SUB connected to " << sub_endpoint << std::endl;
    }

    void stop() {
        if (running) {
            running = false;
            if (router_thread.joinable()) {
                router_thread.join();
            }
            if (sub_thread.joinable()) {
                sub_thread.join();
            }
        }
    }

    void send_command(const std::string& json_str);

private:

    void router_loop() {
        while (running) {
        zmq::multipart_t multipart_msg;
        if (multipart_msg.recv(router_socket, ZMQ_DONTWAIT)) {
            {
                std::lock_guard<std::mutex> lock(client_id_mutex);
                const auto& identity_frame = multipart_msg.front();
                zmq::message_t identity_copy(identity_frame.data(), identity_frame.size());
                python_client_id = std::move(identity_copy);
            }

            std::string received_str = multipart_msg.at(2).to_string();
            try {
                json j = json::parse(received_str);
                if (j.contains("type") && j["type"] == "handshake") {
                    std::cout << "Python client connected with handshake." << std::endl;
                } else if (j.contains("type") && j["type"] == "reply") {
                    if (j.contains("status") && j["status"] == "ok") {
                        reply_svc.update(j.value("payload", "[empty]"));
                    } else {
                        reply_svc.update("Error: " + j.value("message", "[no msg]"));
                    }
                }
            } catch (const json::parse_error& e) {
                reply_svc.update("Error: Malformed JSON from Python.");
            }
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
}

    void subscribe_loop() {
        while (running) {
            zmq::multipart_t multipart_msg;
            if (multipart_msg.recv(sub_socket, ZMQ_DONTWAIT)) { // Or your version's syntax
                std::string topic = multipart_msg.popstr();
                std::string payload = multipart_msg.popstr();

                if (topic == "backend_state") {
                    strncpy(state_buffer, payload.c_str(), sizeof(state_buffer));
                    state_buffer[sizeof(state_buffer) - 1] = '\0';
                    state_svc.updateService();
                }
                else if (topic == "waveform") {
                    strncpy(waveform_buffer, payload.c_str(), sizeof(waveform_buffer));
                    waveform_buffer[sizeof(waveform_buffer) - 1] = '\0';
                    waveform_svc.updateService();
                }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
    }
};

CommandService::CommandService(ZmqCommunicator& comm): 
    DimCommand("SCOPE/COMMAND", "C"), zmq_comm(comm), command_counter(0) {}


void CommandService::commandHandler() {
    std::string cmd_text = getString();
    std::cout << "Received DIM command: " << cmd_text << std::endl;

    json j;
    j["id"] = "cmd_" + std::to_string(command_counter++);
    j["type"] = "command";
    j["command"] = cmd_text; // Or parse it further if needed
    j["params"] = {}; // Add params if any

    zmq_comm.send_command(j.dump());
}


void ZmqCommunicator::send_command(const std::string& json_str) {
    std::lock_guard<std::mutex> lock(client_id_mutex);
    if (python_client_id.size() == 0) {
        reply_svc.update("Error: Python client not connected.");
        return;
    }
    std::cout << "Sending command to Python: " << json_str << std::endl;
    router_socket.send(python_client_id, zmq::send_flags::sndmore);
    router_socket.send(zmq::buffer(""), zmq::send_flags::sndmore);
    router_socket.send(zmq::buffer(json_str), zmq::send_flags::none);
}

class GenericJsonCommand : public DimCommand {
    ZmqCommunicator& zmq_comm;
    std::string python_command;
    std::string param_name;
    long command_counter = 0;

public:
    GenericJsonCommand(ZmqCommunicator& comm, const char* dim_name, const char* dim_format, 
                       const std::string& py_cmd, const std::string& param) :
        DimCommand(dim_name, dim_format),
        zmq_comm(comm),
        python_command(py_cmd),
        param_name(param) {}

    void commandHandler() override {
        json j;
        j["id"] = python_command + "_" + std::to_string(command_counter++);
        j["command"] = python_command;

        // Determine which data type to get based on the format string
        std::string format = getFormat();
        if (format.rfind("I", 0) == 0) { // Starts with "I"
            j["params"][param_name] = getInt();
        } else if (format.rfind("F", 0) == 0 || format.rfind("D", 0) == 0) { // Starts with "F" or "D"
            j["params"][param_name] = getFloat();
        } else { // Default to String
            j["params"][param_name] = getString();
        }
        
        zmq_comm.send_command(j.dump());
    }
};

struct ChannelCommandData {
    int channel;
    float value; // Use float as a universal type for voltage or state (0.0/1.0)
};

class ChannelJsonCommand : public DimCommand {
    ZmqCommunicator& zmq_comm;
    std::string python_command;
    std::string value_param_name;
    long command_counter = 0;

public:
    ChannelJsonCommand(ZmqCommunicator& comm, const char* dim_name, 
                       const std::string& py_cmd, const std::string& value_param) :
        DimCommand(dim_name, "I:1;F:1"), // Expects an integer (channel) and a float (value)
        zmq_comm(comm),
        python_command(py_cmd),
        value_param_name(value_param) {}

    void commandHandler() override {
        ChannelCommandData* data = (ChannelCommandData*)getData();

        json j;
        j["id"] = python_command + "_" + std::to_string(command_counter++);
        j["command"] = python_command;
        j["params"]["channel"] = data->channel;
        j["params"][value_param_name] = data->value;
        
        zmq_comm.send_command(j.dump());
    }
};

class RawCommandService : public DimCommand {
    ZmqCommunicator& zmq_comm;
    long command_counter = 0;
public:
    RawCommandService(ZmqCommunicator& comm) :
        DimCommand("SCOPE/COMMAND", "C"), zmq_comm(comm) {}

    void commandHandler() override {
        std::string cmd_text = getString();
        json j;
        j["id"] = "raw_cmd_" + std::to_string(command_counter++);
        j["type"] = "command";
        if (cmd_text.find('?') != std::string::npos) {
            j["command"] = "raw_query";
            j["params"] = { {"query", cmd_text} };
        } else {
            j["command"] = "raw_write";
            j["params"] = { {"command", cmd_text} };
        }
        zmq_comm.send_command(j.dump());
    }
};


// ===================================================================
// Main Application Entry Point
// ===================================================================
int main() {
    char state_initial_val[] = "UNKNOWN";
    char waveform_initial_val[] = "N/A";

    ReplyService reply_service;

    ZmqCommunicator zmq_comm(reply_service);
    
    DimService state_service("SCOPE/STATE", state_initial_val);
    DimService waveform_service("SCOPE/WAVEFORM", waveform_initial_val);
    RawCommandService raw_cmd(zmq_comm);
    ChannelJsonCommand channel_state_cmd(zmq_comm, "SCOPE/CHANNEL/SET_STATE", "set_channel_state", "state");
    ChannelJsonCommand channel_volts_cmd(zmq_comm, "SCOPE/CHANNEL/SET_VOLTS_DIV", "set_channel_volts", "volts");
    GenericJsonCommand trigger_edge_cmd(zmq_comm, "SCOPE/TRIGGER/SET_EDGE", "C", "set_trigger_edge", "edge");
    GenericJsonCommand trigger_level_cmd(zmq_comm, "SCOPE/TRIGGER/SET_LEVEL", "F", "set_trigger_level", "level");

    GenericJsonCommand acq_control_cmd(zmq_comm, "SCOPE/ACQUISITION_CONTROL", "I", "set_acquisition_state", "state");

    zmq_comm.start("tcp://*:5555", "tcp://localhost:5557"); 
    DimServer::start("OscilloscopeServer");

    std::cout << "DIM Server 'OscilloscopeServer' started." << std::endl;
    std::cout << "Providing services SCOPE/COMMAND and SCOPE/REPLY." << std::endl;

    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(5));
    }

    zmq_comm.stop();
    return 0;
}