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
    std::string buffer;
    DimService reply_service;
    std::mutex mtx;

public:
    ReplyService() :
        buffer("N/A"),
        reply_service("SCOPE/REPLY", (char*)buffer.c_str())
    {
        buffer.reserve(2048);
    }

    void update(const std::string& new_reply) {
        std::lock_guard<std::mutex> lock(mtx);
        if (new_reply.length() + 1 > buffer.capacity()) {
            buffer.reserve(new_reply.length() + 1);
        }
        buffer = new_reply;
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
    CommandService(ZmqCommunicator& comm) :
        DimCommand("SCOPE/COMMAND", "C"),
        zmq_comm(comm),
        command_counter(0) {}

    void commandHandler() override;
};


// ===================================================================
// Handles asynchronous ZMQ communication in a separate thread
// ===================================================================
class ZmqCommunicator {
    zmq::context_t context;
    zmq::socket_t socket;
    std::atomic<bool> running;
    std::thread comm_thread;
    ReplyService& reply_svc;
    zmq::message_t python_client_id;

public:
    ZmqCommunicator(ReplyService& service) :
        context(1),
        socket(context, zmq::socket_type::router),
        running(false),
        reply_svc(service) {}

    ~ZmqCommunicator() {
        stop();
    }

    void start(const std::string& endpoint) {
        socket.bind(endpoint);
        running = true;
        comm_thread = std::thread(&ZmqCommunicator::receive_loop, this);
        std::cout << "ZMQ ROUTER listening on " << endpoint << std::endl;
    }

    void stop() {
        if (running) {
            running = false;
            if (comm_thread.joinable()) {
                comm_thread.join();
            }
        }
    }

    void send_command(const std::string& cmd_text, const std::string& cmd_id);

private:
    void receive_loop() {
        while (running) {
            zmq::multipart_t multipart_msg;

            bool result = multipart_msg.recv(socket, static_cast<int>(zmq::recv_flags::dontwait));

            if (!result) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                continue;
            }

            if (multipart_msg.size() < 2) {
                std::cerr << "Warning: Received malformed message with " << multipart_msg.size() << " parts. Ignoring." << std::endl;
                continue;
            }

            // --- THIS IS THE CORRECT, COMPILABLE LINE ---
            // It creates a new message by copying the raw data from the first frame.
            python_client_id = zmq::message_t(multipart_msg.front().data(), multipart_msg.front().size());

            // The payload is always the LAST part.
            std::string received_str = multipart_msg.back().to_string();

            std::cout << "Received message from Python: " << received_str << std::endl;

            try {
                json j = json::parse(received_str);
                if (j.contains("type") && j["type"] == "reply") {
                    reply_svc.update(j["payload"].get<std::string>());
                }
                else if (j.contains("type") && j["type"] == "status") {
                    std::cout << "Status update from Python worker: " << j["payload"].get<std::string>() << std::endl;
                }
            } catch (const json::parse_error& e) {
                std::cerr << "JSON parse error: " << e.what() << std::endl;
                reply_svc.update("Error: Received malformed JSON from Python.");
            }
        }
    }
};

// Implementation of CommandService::commandHandler
void CommandService::commandHandler() {
    std::string cmd = getString();
    std::cout << "Received DIM command: " << cmd << std::endl;
    std::string cmd_id = "cmd_" + std::to_string(command_counter++);
    zmq_comm.send_command(cmd, cmd_id);
}

// Must define this after the full class definition of ZmqCommunicator
void ZmqCommunicator::send_command(const std::string& cmd_text, const std::string& cmd_id) {
    if (!python_client_id.size()) {
        std::cerr << "Error: Python client has not connected yet. Cannot send command." << std::endl;
        reply_svc.update("Error: Python client not connected.");
        return;
    }

    json j;
    j["type"] = "command";
    j["id"] = cmd_id;
    j["payload"] = cmd_text;

    std::string msg_str = j.dump();
    std::cout << "Sending command to Python: " << msg_str << std::endl;

    // Send a 3-part message: [identity, empty_delimiter, content]
    // This is the most robust way to ensure compatibility.
    socket.send(python_client_id, zmq::send_flags::sndmore);
    socket.send(zmq::buffer(""), zmq::send_flags::sndmore);
    socket.send(zmq::buffer(msg_str), zmq::send_flags::none);
}

// ===================================================================
// Main Application Entry Point
// ===================================================================
int main() {
    ReplyService reply_service;
    ZmqCommunicator zmq_comm(reply_service);
    CommandService command_service(zmq_comm);

    zmq_comm.start("tcp://*:5555");
    DimServer::start("OscilloscopeServer");

    std::cout << "DIM Server 'OscilloscopeServer' started." << std::endl;
    std::cout << "Providing services SCOPE/COMMAND and SCOPE/REPLY." << std::endl;

    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(5));
    }

    zmq_comm.stop();
    return 0;
}