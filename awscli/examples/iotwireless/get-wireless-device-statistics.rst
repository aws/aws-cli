**To get operating information about a wireless device**

The following ``get-wireless-device-statistics`` example gets operating information about a wireless device. ::

    aws iotwireless get-wireless-device-statistics \
        --wireless-device-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "WirelessDeviceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.
