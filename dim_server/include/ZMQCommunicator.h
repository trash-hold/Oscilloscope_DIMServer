#pragma once
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>

// Internal libraries
#include "DimServices.h"

// External libraries
#include <zmq.hpp>
#include <dis.hxx> 

// Forward declaration to avoid circular dependencies
class ReplyService;

class ZmqCommunicator {
    zmq::context_t context;
    std::mutex client_id_mutex;
    std::atomic<bool> running;
    zmq::message_t python_client_id;

    // Sockets
    zmq::socket_t router_socket;
    zmq::socket_t sub_socket;

    // Threads
    std::thread router_thread;
    std::thread sub_thread;

    // Services
    ReplyService& reply_svc;
    ProtectedDimService state_svc;
    std::vector<std::unique_ptr<ProtectedDimService>> waveform_svcs;

public:
    ZmqCommunicator(ReplyService& service);
    ~ZmqCommunicator();

    void start(const std::string& router_endpoint, const std::string& sub_endpoint);
    void stop();
    void send_command(const std::string& json_str);

private:
    void router_loop();
    void subscribe_loop();
};