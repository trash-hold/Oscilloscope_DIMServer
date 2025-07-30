#include "ZMQCommunicator.h"
#include "DimServices.h"
#include "Constants.h"

// Standard CPP libraries
#include <iostream>
#include <chrono>
#include <memory>

// Outside dependencies
#include <zmq_addon.hpp>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

ZmqCommunicator::ZmqCommunicator(ReplyService& service) :
    context(1),
    running(false),
    router_socket(context, zmq::socket_type::router),
    sub_socket(context, zmq::socket_type::sub),
    reply_svc(service),
    state_svc(Constants::STATE_SERVICE, Constants::STATE_BUFFER_SIZE),
    timediv_svc(Constants::TIMEDIV_SERVICE, Constants::STATE_BUFFER_SIZE)
{
    // Create and store the 4 waveform services
    for (int i = 0; i < Constants::OSC_NUM_CHANNELS; ++i) {
        std::string service_name = Constants::WAVEFORM_SERVICE_BASE + std::to_string(i + 1);
        waveform_svcs.push_back(std::make_unique<ProtectedDimService>(service_name, Constants::WAVEFORM_BUFFER_SIZE));
    }
}

ZmqCommunicator::~ZmqCommunicator() {
    stop();
}

void ZmqCommunicator::start(const std::string& router_endpoint, const std::string& sub_endpoint) {
    router_socket.bind(router_endpoint);
    sub_socket.connect(sub_endpoint);

    sub_socket.set(zmq::sockopt::subscribe, Constants::ZMQ_STATE_TOPIC);
    sub_socket.set(zmq::sockopt::subscribe, Constants::ZMQ_TIMEDIV_TOPIC);

    // Subscribe to each of the 4 new waveform topics
    for (int i = 0; i < Constants::OSC_NUM_CHANNELS; ++i) {
        std::string topic_name = Constants::ZMQ_WAVEFORM_TOPIC_BASE + std::to_string(i + 1);
        sub_socket.set(zmq::sockopt::subscribe, topic_name);
        std::cout << "Subscribed to ZMQ topic: " << topic_name << std::endl;
    }

    running = true;
    router_thread = std::thread(&ZmqCommunicator::router_loop, this);
    sub_thread = std::thread(&ZmqCommunicator::subscribe_loop, this);
    std::cout << "ZMQ ROUTER listening on " << router_endpoint << std::endl;
    std::cout << "ZMQ SUB connected to " << sub_endpoint << std::endl;
}

void ZmqCommunicator::stop() {
    if (running) {
        running = false;
        if (router_thread.joinable()) router_thread.join();
        if (sub_thread.joinable()) sub_thread.join();
    }
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

void ZmqCommunicator::router_loop() {
    while (running) {
        zmq::multipart_t multipart_msg;
        if (multipart_msg.recv(router_socket, ZMQ_DONTWAIT)) {
            {
                std::lock_guard<std::mutex> lock(client_id_mutex);
                python_client_id = std::move(multipart_msg.at(0));
            }

            std::string received_str = multipart_msg.at(2).to_string();
            try {
                json j = json::parse(received_str);
                if (j.value(Constants::JSON_TYPE, "") == "handshake") {
                    std::cout << "Python client connected with handshake." << std::endl;
                } else if (j.value(Constants::JSON_TYPE, "") == "reply") {
                    if (j.value(Constants::JSON_STATUS, "") == "ok") {
                        reply_svc.update(j.value(Constants::JSON_PAYLOAD, "[empty]"));
                    } else {
                        reply_svc.update("Error: " + j.value(Constants::JSON_MESSAGE, "[no msg]"));
                    }
                }
            } catch (const json::parse_error& e) {
                reply_svc.update("Error: Malformed JSON from Python.");
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

void ZmqCommunicator::subscribe_loop() {
    while (running) {
        zmq::multipart_t multipart_msg;
        if (multipart_msg.recv(sub_socket, ZMQ_DONTWAIT)) {
            std::string topic = multipart_msg.popstr();
            std::string payload = multipart_msg.popstr();

            if (topic == Constants::ZMQ_STATE_TOPIC) {
                state_svc.update(payload);
            }
            else if(topic == Constants::ZMQ_TIMEDIV_TOPIC){
                timediv_svc.update(payload);
            }
            else if (topic.rfind(Constants::ZMQ_WAVEFORM_TOPIC_BASE, 0) == 0) {
                try {
                    // Extract channel number from topic string (e.g., "waveform_ch1" -> 0)
                    std::string ch_str = topic.substr(Constants::ZMQ_WAVEFORM_TOPIC_BASE.length());
                    int ch_index = std::stoi(ch_str) - 1;

                    if (ch_index >= 0 && ch_index < Constants::OSC_NUM_CHANNELS) {
                        // Call the thread-safe update on the correct service
                        waveform_svcs[ch_index]->update(payload);
                    }
                } catch (const std::exception& e) {
                    // Handle cases like "waveform_chABC" or out-of-range index
                    std::cerr << "Error processing topic '" << topic << "': " << e.what() << std::endl;
                }
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10)); // Reduced sleep for better responsiveness
    }
}