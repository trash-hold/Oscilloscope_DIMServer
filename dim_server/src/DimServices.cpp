#include "DimServices.h"
#include "Constants.h"
#include <iostream>

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