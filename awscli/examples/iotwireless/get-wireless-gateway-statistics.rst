**To get operating information about a wireless gateway**

The following ``get-wireless-gateway-statistics`` example gets operating information about a wireless gateway. ::

    aws iotwireless get-wireless-gateway-statistics \
        --wireless-gateway-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "WirelessGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.
