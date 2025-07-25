#include "ZMQCommunicator.h"
#include "DimServices.h"
#include "Constants.h"
#include <iostream>
#include <chrono>
#include <zmq_addon.hpp>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

ZmqCommunicator::ZmqCommunicator(ReplyService& service) :
    context(1),
    running(false),
    router_socket(context, zmq::socket_type::router),
    sub_socket(context, zmq::socket_type::sub),
    reply_svc(service),
    state_svc(Constants::STATE_SERVICE, state_buffer),
    waveform_svc(Constants::WAVEFORM_SERVICE, waveform_buffer)
{
    state_buffer[0] = '\0';
    waveform_buffer[0] = '\0';
}

ZmqCommunicator::~ZmqCommunicator() {
    stop();
}

void ZmqCommunicator::start(const std::string& router_endpoint, const std::string& sub_endpoint) {
    router_socket.bind(router_endpoint);
    sub_socket.connect(sub_endpoint);
    sub_socket.set(zmq::sockopt::subscribe, Constants::ZMQ_STATE_TOPIC);
    sub_socket.set(zmq::sockopt::subscribe, Constants::ZMQ_WAVEFORM_TOPIC);

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
                strncpy(state_buffer, payload.c_str(), sizeof(state_buffer) - 1);
                state_buffer[sizeof(state_buffer) - 1] = '\0';
                state_svc.updateService();
            } else if (topic == Constants::ZMQ_WAVEFORM_TOPIC) {
                strncpy(waveform_buffer, payload.c_str(), sizeof(waveform_buffer) - 1);
                waveform_buffer[sizeof(waveform_buffer) - 1] = '\0';
                waveform_svc.updateService();
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
}