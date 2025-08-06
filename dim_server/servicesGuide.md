
## DIM Server User Manual

### Overview

This guide describes the DIM services available on the server and the logic behind their operation. The terms **read** and **write** are used from the client's perspective.

Input values in this document are enclosed in angle brackets, for example: `<value>`.

> **Warning**
> It is strongly advised not to change any oscilloscope settings while an acquisition is in progress.

---

### Data Acquisition

Services used for the data acquisition process.
**Service Prefix:** `SCOPE/ACQUISITION/`

*   #### `CH<x>`
    A read-only service that publishes the data acquired from an oscilloscope channel. There are four separate services, one for each channel (`CH1`, `CH2`, `CH3`, `CH4`).
    *   **Data Format:** A string containing 10,000 float samples in scientific notation, separated by commas (`,`). The maximum length of a single sample string is 13 characters.

*   #### `SET_MODE`
    A write service that sets the acquisition mode.
    *   **Accepted Values:**
        *   `OFF`: Stops the acquisition after the current measurement is complete.
        *   `SINGLE`: Performs a single acquisition and publishes the data.
        *   `CONT`: Continuously acquires and publishes data until the mode is set to `OFF` or a timeout error occurs.

*   #### `SET_TIMEOUT`
    A write service that sets the maximum time allowed for a single acquisition to complete before raising an error.
    *   **Input:** `<float>` (Value in seconds)

*   #### `IGNORE_TIMEOUT`
    A write service that controls the timeout behavior. If set to `true`, a timeout error will be ignored, and the `CONT` mode will not be interrupted.
    *   **Input:** `<integer>` (`1` for true, `0` for false)

*   #### `SET_TIMEDIV`
    A write service that sets the horizontal scale (time per division) of the oscilloscope.
    *   **Input:** `<float>` (Standard or scientific notation is acceptable)

---

### Channel Settings

Services used to configure the individual oscilloscope channels.
**Service Prefix:** `SCOPE/CHANNEL/`

*   #### `SET_ENABLED`
    A write service to enable or disable a specific channel.
    *   **Format:** `<channel_number>;<state>`
    *   **Example:** `1;1` (Enables Channel 1)
    *   **Values:**
        *   `<channel_number>`: integer
        *   `<state>`: `1` for ON, `0` for OFF

*   #### `SET_SCALE`
    A write service that sets the vertical scale (volts per division) for a specific channel.
    *   **Format:** `<channel_number>;<scale>`
    *   **Example:** `1;5.0e-3` (Sets the scale of Channel 1 to 5mV)
    *   **Values:**
        *   `<channel_number>`: integer
        *   `<scale>`: float (Standard or scientific notation is acceptable)

---

### Trigger Settings

Services used to configure the trigger.
**Service Prefix:** `SCOPE/TRIGGER/`

*   #### `SET_CHANNEL`
    A write service that sets the source channel for the trigger.
    *   **Input:** `<integer>` (Channel number)

*   #### `SET_LEVEL`
    A write service that sets the trigger level in volts.
    *   **Input:** `<float>` (Standard or scientific notation is acceptable)

*   #### `SET_SLOPE`
    A write service that sets the edge for the trigger.
    *   **Accepted Values:**
        *   `RISE`: For a rising edge trigger.
        *   `FALL`: For a falling edge trigger.

---

### Special Services

General-purpose services.
**Service Prefix:** `SCOPE/`

*   #### `RAW`
    A write service for sending raw SCPI commands directly to the oscilloscope.
    *   **Input:** `<string>` (A valid SCPI command)
    *   **Note:** If the command is a query (e.g., ends with `?`), the oscilloscope's response will be published to the `REPLY` service.

*   #### `REPLY`
    A read-only service that publishes responses and status messages from the server and oscilloscope. This includes:
    *   Replies from queries sent via the `RAW` service.
    *   Error messages.
    *   Status updates on current operations.

*   #### `TIMEDIV`
    A read-only service that provides the time increment (in seconds) between individual samples in the acquired data.