## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Installation and Setup](#installation-and-setup)
  - [Prerequisites](#prerequisites)
  - [1. Install the DIM Library](#1-install-the-dim-library)
  - [2. Clone Repository and Install Python Dependencies](#2-clone-repository-and-install-python-dependencies)
  - [3. Build the Project's DIM Server](#3-build-the-projects-dim-server)
- [Configuration](#configuration)
- [How to Run the System](#how-to-run-the-system)
- [Expanding the System](#expanding-the-system)
  - [Adding a Write-Only DIM Service](#adding-a-write-only-dim-service)
  - [Adding a Read-Only DIM Service](#adding-a-read-only-dim-service)
  - [Adding New Oscilloscope Drivers](#adding-new-oscilloscope-drivers)

## Overview

This repository provides a complete system for controlling an oscilloscope via a Python application and a C++ DIM server. It includes:

-   A C++ **DIM server** that exposes oscilloscope controls to the DIM network.
-   A **Python application** that acts as a backend, communicating with the DIM server via ZMQ. It can be run with a GUI or in headless mode.
-   A **driver framework** for extending functionality to different oscilloscopes, with a ready-to-use driver for the **Tektronix TDS3054C**.

## Features

-   **Remote Control:** Manage and monitor an oscilloscope over the network.
-   **GUI & Headless Modes:** Operate through a user-friendly PySide6 GUI or run as a background service.
-   **Extensible:** Easily add new commands (services) or support for new oscilloscope models.
-   **Decoupled Architecture:** A robust C++/Python architecture connected by ZMQ messaging ensures stability and separation of concerns.

## System Architecture

The system consists of two main components:
1.  **C++ DIM Server:** This application listens for commands from DIM clients on the network. When it receives a command, it translates it and forwards it to the Python backend via a ZMQ socket. It also subscribes to topics from the Python backend to receive data that can be published as read-only DIM services.
2.  **Python Application:** This backend contains the instrument-specific logic. It listens for commands from the C++ server via ZMQ, processes them using the appropriate driver, and can publish data (like device state or acquired waveforms) back to the C++ server.

---

## Installation and Setup

### Prerequisites

-   **Python:** The GUI requires **Python 3.9+**. Headless mode has been tested with Python 3.6 and 3.9.
-   **Operating System:** The DIM library build process has been successfully tested on **RedHat** and **Ubuntu**.
-   **Build Tools:** A C++ compiler (`g++`), `gmake`/`make`, and `CMake`.

### 1. Install the DIM Library

To install DIM, visit [the official DIM website](https://dim.web.cern.ch/) and download the appropriate `zip` or `tar` files.

**Note:** Building DIM can be challenging. The following steps provide a guide for Linux-based systems.

1.  **Set Environment Variables:**
    -   `DIMDIR`: Should point to the root directory of the unpacked DIM library.
    -   `OS`: Choose the closest match from the following: `HP-UX`, `AIX`, `Solaris`, `SunOS`, `OSF1`, `Linux`, `LynxOS`, `Darwin`.
    -   `DIM_DNS_NODE`: Set this to your machine's local or public IP address.
    -   `DIM_DNS_PORT`: The default is `2505`. You can change it if needed.

2.  **Build the Library:**
    ```bash
    cd $DIMDIR/dim
    source .setup
    gmake clean
    gmake all
    ```

3.  **Troubleshooting the DIM Build:**
    -   **Missing Packages:** If you encounter errors about missing packages (common on a fresh Ubuntu installation), use your system's package manager (e.g., `apt`, `yum`) to install the required development libraries based on the compiler errors.
    -   **Check the Build:** To verify the build, navigate to the `$DIMDIR/linux` directory (or your OS equivalent) and run the `dns` executable. In another terminal, run `checkDns` to see if the DNS is visible.
    -   **Firewall Issues:** If other clients cannot see your DIM services, a firewall is the most likely cause. Ensure that traffic is allowed on the `DIM_DNS_PORT` (e.g., 2505) and other DIM-related ports (e.g., 2500, 5100-5110).

### 2. Clone Repository and Install Python Dependencies

```bash
git clone <your-repository-url>
cd <repository-directory>
pip install -r requirements.txt
```
The `requirements.txt` file contains all packages for both GUI and headless modes. You may prune this list if you do not need the GUI or the included Tektronix driver.

### 3. Build the Project's DIM Server

The C++ DIM server included in this repository must be built before use. All libraries and dependencies are defined in the `CMakeLists.txt` file.

```bash
cd <path-to-your-c++-server-directory>
mkdir build && cd build
cmake ..
make
```

---

## Configuration

Before running the system, you must set up your configuration files. Templates are provided in the `/config` directory.

1.  **`config.json`**: This is the main configuration file. It defines socket addresses and DIM connection details.
    -   **Note:** The ports for the DIM server can be changed in `Constants.h` in the C++ server code.
2.  **`XXX_profile.json`**: This file describes device-specific information and functionality. Its structure depends on the driver implementation. Please see the example `TDS3054C_profile.json` for context.

By default, the Python application looks for `config.json` in a `/secret` directory at the project root. You must create this directory yourself. It is included in `.gitignore` for security.

**IMPORTANT: If you place your configuration in a different directory, you must update the path in `gui_zmq.py` and `headless_zmq.py`.**

## How to Run the System

After completing the installation and configuration, follow these steps to start the system:

1.  **Start the C++ DIM Server** by running the executable you built.
2.  **Start the Python Application** by running either `gui_zmq.py` or `headless_zmq.py`.

Enjoy!

---

## Expanding the System

### Adding a Write-Only DIM Service

To add a new service that allows DIM clients to write data (e.g., change a setting), follow these steps:

1.  **Define Constants in C++ and Python:**
    -   In `Constants.h` (C++), add two constants: one for the public DIM service name and one for the internal ZMQ command string.
        ```cpp
        constexpr const char* CHAN_SET_ENABLED_CMD = "SCOPE/CHANNEL/SET_ENABLED"; // Public DIM name
        constexpr const char* PY_SET_CHAN_ENABLED = "set_channel_enabled";       // Internal ZMQ command
        ```
    -   In `common/constants.py` (Python), add the matching command string.
        ```python
        SET_CHANNEL_ENABLED = "set_channel_enabled"
        ```
        **Ensure the string in C++ matches the Python constant exactly.**

2.  **Register the New Service in C++:**
    -   In `CommandRegistry.cpp`, add your new service. You can use existing classes like `FlexibleJsonCommand` or create a new one.
        ```cpp
        new FlexibleJsonCommand(comm, Constants::CHAN_SET_ENABLED_CMD, "I", Constants::PY_SET_CHAN_ENABLED,
            [](DimCommand* cmd, json& params) {
                params["channel"] = cmd->getInt();
            }
        );
        ```

3.  **Implement the Backend Logic in Python:**
    -   In `manager/backend.py`, locate the `self.COMMAND_MAP` dictionary. Add your new command and a corresponding handler function, following the existing examples.

4.  **(Optional) Add Driver-Specific Logic:** If the command requires new, device-specific behavior, add the necessary methods to the `DeviceManager` and the relevant driver class.

### Adding a Read-Only DIM Service

To add a new service that publishes data from Python to DIM clients, follow these steps:

1.  **Define a ZMQ Topic Constant:**
    -   In `Constants.h` (C++), add a constant for the ZMQ topic that the service will subscribe to.
        ```cpp
        constexpr const char* ZMQ_STATE_TOPIC = "backend_state";
        ```

2.  **Add the Service in `ZmqCommunicator.h`:**
    -   Declare a new `ProtectedDimService` (or a custom service class).
        ```cpp
        ProtectedDimService state_svc;
        ```

3.  **Subscribe to the Topic in `ZmqCommunicator.cpp`:**
    -   In the `start()` function, subscribe the ZMQ socket to your new topic.
        ```cpp
        sub_socket.set(zmq::sockopt::subscribe, Constants::ZMQ_STATE_TOPIC);
        ```
    -   In the `subscribe_loop()` function, add logic to route messages from this topic to your service's update method.
        ```cpp
        if (topic == Constants::ZMQ_STATE_TOPIC) {
            state_svc.update(payload);
        }
        ```

4.  **Publish Data from Python:**
    -   Use the `ZmqCommunicator.reply_to_dim()` function in your Python code to publish a message with the correct topic. See the `_perform_one_acquisition_cycle` function in `manager/backend.py` for an example.

---

## Adding New Oscilloscope Drivers

To add support for a new oscilloscope, you must:

1.  **Create a New Driver Class:**
    -   Create a new Python class that inherits from the `Oscilloscope` class in `drivers/AbstractInterfaces.py`. You will need to implement the driver's logic.
    -   **Tip:** Many oscilloscopes use the **SCPI** (Standard Commands for Programmable Instruments) protocol, so the provided Tektronix driver may serve as a useful, partially compatible reference.

2.  **Register the New Driver:**
    -   Add the new driver class to the `DRIVER_MAP` dictionary in `common/driver_map.py`.

3.  **Create Configuration Files:**
    -   Create a new `XXX_profile.json` file that contains the device-specific configuration for your new driver.

4.  **Update Main Config:**
    -   Update your `config.json` to point to the new driver name and profile JSON file.
