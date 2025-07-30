#pragma once
#include <vector>
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

class ProtectedDimService {
public:
    // Constructor takes the DIM service name and the size for its internal buffer.
    ProtectedDimService(const std::string& name, size_t buffer_size);

    ProtectedDimService(const ProtectedDimService&) = delete;
    ProtectedDimService& operator=(const ProtectedDimService&) = delete;

    void update(const std::string& new_data);

private:
    std::mutex mtx;
    std::vector<char> buffer;
    DimService service;
};