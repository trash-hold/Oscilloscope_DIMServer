#include "DimServices.h"
#include "Constants.h"
#include <iostream>

ProtectedDimService::ProtectedDimService(const std::string& name, size_t buffer_size) :
    buffer(buffer_size, '\0'), // Allocate buffer and initialize to null characters
    service(name.c_str(), buffer.data())
{
}

void ProtectedDimService::update(const std::string& new_data) {
    std::lock_guard<std::mutex> lock(mtx);
    // Use strncpy to copy data, ensuring null termination.
    strncpy(buffer.data(), new_data.c_str(), buffer.size() - 1);
    buffer.back() = '\0'; // Ensure the last character is always null.
    service.updateService();
    // For debugging:
    // std::cout << "Updated " << service.getName() << " with data of size " << new_data.length() << std::endl;
}

ReplyService::ReplyService() :
    reply_service(Constants::REPLY_SERVICE, buffer)
{
    buffer[0] = '\0';
}

void ReplyService::update(const std::string& new_reply) {
    std::lock_guard<std::mutex> lock(mtx);
    strncpy(buffer, new_reply.c_str(), sizeof(buffer));
    buffer[sizeof(buffer) - 1] = '\0';
    reply_service.updateService();
    std::cout << "Updated " << Constants::REPLY_SERVICE << " with: " << buffer << std::endl;
}