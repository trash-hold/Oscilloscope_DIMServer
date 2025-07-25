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

    void send_command(const std::string& cmd_text, const std::string& cmd_id);

private:

    void router_loop() {
        while (running) {
            zmq::multipart_t multipart_msg;
            
            bool result = multipart_msg.recv(router_socket, static_cast<int>(zmq::recv_flags::dontwait));
            if (!result) {
                // No message received, sleep and continue
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                continue;
            }

            const auto& identity_frame = multipart_msg.front();
            zmq::message_t identity_copy(identity_frame.data(), identity_frame.size());
            // Then move this new, independent message into our class member.
            python_client_id = std::move(identity_copy);

            std::string received_str = multipart_msg.at(2).to_string();

            try {
                json j = json::parse(received_str);

                // --- ROBUST PARSING FIX ---
                if (j.contains("type") && j["type"].is_string()) {
                    std::string msg_type = j["type"];

                    if (msg_type == "handshake") {
                        std::cout << "Python client connected with handshake." << std::endl;
                    } 
                    else if (msg_type == "reply") {
                        std::cout << "Received reply from Python: " << received_str << std::endl;
                        
                        if (j.contains("status") && j["status"] == "ok") {
                            // Check for payload and ensure it's a string before using
                            if (j.contains("payload") && j["payload"].is_string()) {
                                reply_svc.update(j["payload"]);
                            } else {
                                reply_svc.update("[OK reply received, but payload is missing or not a string]");
                            }
                        } else {
                            // Check for message and ensure it's a string before using
                            if (j.contains("message") && j["message"].is_string()) {
                                reply_svc.update("Error from Python: " + j["message"].get<std::string>());
                            } else {
                                reply_svc.update("Error reply from Python, but message field is missing.");
                            }
                        }
                    }
                } else {
                    std::cerr << "Received message from Python with no 'type' field: " << received_str << std::endl;
                }

            } catch (const json::parse_error& e) {
                std::cerr << "JSON parse error: " << e.what() << std::endl;
                reply_svc.update("Error: Received malformed JSON from Python.");
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
    std::string cmd = getString();
    std::cout << "Received DIM command: " << cmd << std::endl;
    std::string cmd_id = "cmd_" + std::to_string(command_counter++);
    zmq_comm.send_command(cmd, cmd_id);
}


void ZmqCommunicator::send_command(const std::string& cmd_text, const std::string& cmd_id) {
    if (!python_client_id.size()) {
        std::cerr << "Error: Python client has not connected yet. Cannot send command." << std::endl;
        reply_svc.update("Error: Python client not connected.");
        return;
    }

    json j;
    j["type"] = "command";
    j["id"] = cmd_id;

    if (cmd_text.find('?') != std::string::npos) {
            j["command"] = "raw_query";
            j["params"] = { {"query", cmd_text} };
    } else {
        j["command"] = "raw_write";
        j["params"] = { {"command", cmd_text} };
    }

    std::string msg_str = j.dump();
    std::cout << "Sending command to Python: " << msg_str << std::endl;

    // Send a 3-part message: [identity, empty_delimiter, content]
    // This is the most robust way to ensure compatibility.
    router_socket.send(python_client_id, zmq::send_flags::sndmore);
    router_socket.send(zmq::buffer(""), zmq::send_flags::sndmore);
    router_socket.send(zmq::buffer(msg_str), zmq::send_flags::none);
}

// ===================================================================
// Main Application Entry Point
// ===================================================================
int main() {
    char state_initial_val[] = "UNKNOWN";
    char waveform_initial_val[] = "N/A";

    ReplyService reply_service;
    DimService state_service("SCOPE/STATE", state_initial_val);
    DimService waveform_service("SCOPE/WAVEFORM", waveform_initial_val);
    
    ZmqCommunicator zmq_comm(reply_service);
    CommandService command_service(zmq_comm);

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