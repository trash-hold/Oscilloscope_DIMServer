#include "ZMQCommunicator.h"
#include "DimServices.h"
#include "CommandRegistry.h"
#include "Constants.h"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    ReplyService reply_service;
    ZmqCommunicator zmq_comm(reply_service);

    // This single function call creates and registers all our commands.
    // To add a new command, you just modify the lists in CommandRegistry.cpp
    register_all_commands(zmq_comm);

    zmq_comm.start(Constants::ZMQ_ROUTER_ENDPOINT, Constants::ZMQ_SUB_ENDPOINT);
    
    DimServer::start(Constants::SERVER_NAME);
    std::cout << "DIM Server '" << Constants::SERVER_NAME << "' started." << std::endl;

    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(5));
    }

    zmq_comm.stop();
    return 0;
}