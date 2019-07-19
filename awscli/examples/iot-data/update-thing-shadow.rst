**To get the current state of a device shadow**

The following ``get-thing-shadow`` example gets the current state of the device shadow for the thing named ``MyRPi`` and saves it to the file ``output.txt``. ::

    aws iot-data get-thing-shadow \
        --thing-name MyRPi \
        "output.txt"

The command produces no output on the display, but the following shows the contents of output.txt::

    {"state":{"reported":{"moisture":"low"}},"metadata":{"reported":{"moisture":{"timestamp":1560269319}}},"version":1,"timestamp":1560269405}

For more information, see `Device Shadow Service Data Flow <https://docs.aws.amazon.com/iot/latest/developerguide/device-shadow-data-flow.html>`__ in the *AWS IoT Developers Guide*.

