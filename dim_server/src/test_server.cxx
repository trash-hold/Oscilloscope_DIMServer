#include <iostream>
#include <dis.hxx>
#ifndef WIN32
#include <unistd.h>
#endif
using namespace std;
#include <string>
#include <vector>
#include <zmq.hpp>  // For interfacing python app
#include <msgpack.hpp>  // For decoding msg from zmq socket

class ErrorHandler : public DimErrorHandler
{
	void errorHandler(int severity, int code, char *msg)
	{
		int index = 0;
		char **services;
		cout << severity << " " << msg << endl;
		services = DimServer::getClientServices();
		cout<< "from "<< DimServer::getClientName() << " services:" << endl;
		while(services[index])
		{
			cout << services[index] << endl;
			index++;
		}
	}
public:
	ErrorHandler() {DimServer::addErrorHandler(this);}
};

class ExitHandler : public DimExitHandler
{
	void exitHandler(int code)
	{
		cout << "exit code " << code << endl;
	}
public:
	ExitHandler() {DimServer::addExitHandler(this);}
};

class CmndServ : public DimCommand, public DimTimer
{
	DimService servstr;
	void commandHandler()
	{
		int index = 0;
		char **services;
		cout << "Command " << getString() << " received" << endl;
		servstr.updateService(getString()); 
		services = DimServer::getClientServices();
		cout<< "from "<< DimServer::getClientName() << " services:" << endl;
		while(services[index])
		{
			cout << services[index] << endl;
			index++;
		}
	}
public :
	CmndServ() : DimCommand("TEST/CMND","C"), 
				 servstr("TEST/STRVAL","empty") {};
};

void add_serv(const int & ival)
{
	DimService *abc;

	abc = new DimService("TEST/INTVAL_CONST",(int &)ival);
}

void add_serv_str(const string & s1)
{
	DimService *abc;

	abc = new DimService("TEST/STRINGVAL_CONST",(char *)s1.c_str());
}

void add_serv_bool(const bool & boolval)
{
	DimService *serv;

//	serv = new DimService("TEST/BOOLVAL_CONST",(short &)boolval);
	serv = new DimService("TEST/BOOLVAL_CONST","C:1", (void *)&boolval, 1);
}

class ServWithHandler : public DimService
{
	int value;

	void serviceHandler()
	{
		value++;
//		setData(value);
	}
public :
	ServWithHandler(char *name) : DimService(name, value) { value = 0;};
};

void runZMQ(DimService *dim_service, std::string *buffer)
{
    // 1. Prepare context and socket
    zmq::context_t context(1);
    zmq::socket_t socket(context, zmq::socket_type::rep);
    socket.bind("tcp://*:5555");

     
    std::stringstream float_converter;
    while (true) {
        // --- Stage 1: Wait for metadata ---
        zmq::message_t metadata_msg;
        socket.recv(metadata_msg, zmq::recv_flags::none);
        std::cout << "Received metadata. Preparing for data..." << std::endl;
        
        // Send "READY" confirmation
        socket.send(zmq::buffer("READY", 5), zmq::send_flags::none);

        // --- Stage 2: Wait for waveform data ---
        zmq::message_t waveform_msg;
        socket.recv(waveform_msg, zmq::recv_flags::none);
        std::cout << "Received waveform data. Processing..." << std::endl;
        
        msgpack::object_handle oh = msgpack::unpack(static_cast<const char*>(waveform_msg.data()), waveform_msg.size());
        std::vector<float> received_floats;
        oh.get().convert(received_floats);
        
        char* write_ptr = buffer->data();
        const char* buffer_end = write_ptr + buffer->capacity();
        size_t total_bytes_written = 0;

        // 2. Loop through floats and write directly into the buffer.
        for (size_t i = 0; i < received_floats.size(); ++i) {
            // Clear the converter for the next float
            float_converter.str("");
            float_converter.clear();
            
            // Convert one float to a string
            float_converter << received_floats[i];
            std::string float_str = float_converter.str();

            // Add a semicolon for all but the last element
            if (i < received_floats.size() - 1) {
                float_str += ';';
            }

            // 3. Check for buffer overflow before writing.
            if (write_ptr + float_str.length() >= buffer_end) {
                std::cerr << "Error: Buffer capacity reached. Truncating data." << std::endl;
                break; // Exit the loop
            }

            // 4. Copy the small string into the main buffer and advance the pointer.
            memcpy(write_ptr, float_str.c_str(), float_str.length());
            write_ptr += float_str.length();
            total_bytes_written += float_str.length();
        }

        // 5. Add the final null terminator at the end of the data.
        *write_ptr = '\0';

        // 6. IMPORTANT: Update the size of the original string object.
        buffer->resize(total_bytes_written);

        // 7. UPDATE THE DIM SERVICE
        dim_service->updateService();

        // --- CORRECT REPLY FOR STAGE 2 ---
        // Send final "ACK" to acknowledge the data
        socket.send(zmq::buffer("ACK", 3), zmq::send_flags::none); 
        
        std::cout << "Cycle complete. Waiting for next metadata." << std::endl;
    }
}

int main()
{
    // Setting up DIM server
    std::string data_str;
    data_str.reserve(10000 * 16);

    DimService waveform_service("SCOPE/WAVEFORM", const_cast<char*>(data_str.c_str()));

    DimServer::start("OscilloscopeData");

    try {
        runZMQ(&waveform_service, &data_str);
    } catch (const zmq::error_t& e) {
        // Catch and report any ZeroMQ-specific errors
        std::cerr << "ZeroMQ error: " << e.what() << " (Error code: " << e.num() << ")" << std::endl;
        return 1;
    } catch (const std::exception& e) {
        // Catch any other standard exceptions
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
	
}

