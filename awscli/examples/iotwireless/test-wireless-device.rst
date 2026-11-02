**To test the wireless device**

The following ``test-wireless-device`` example sends uplink data of ``Hello`` to a device with specified ID. ::

    aws iotwireless test-wireless-device \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Result": "Test succeeded. one message is sent with payload: hello"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.