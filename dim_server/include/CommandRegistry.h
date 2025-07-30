#pragma once

class ZmqCommunicator; // Forward declaration

// Creates and registers all DIM commands for the server.
void register_all_commands(ZmqCommunicator& comm);