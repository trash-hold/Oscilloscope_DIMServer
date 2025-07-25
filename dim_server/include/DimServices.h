#pragma once
#include <string>
#include <mutex>
#include <dis.hxx>

class ReplyService {
    char buffer[2048];
    DimService reply_service;
    std::mutex mtx;

public:
    ReplyService();
    void update(const std::string& new_reply);
};