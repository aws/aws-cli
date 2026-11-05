**To get information about the wireless gateway task**

The following ``get-wireless-gateway-task`` example gets information about the wireless gateway task with the specified ID. ::

    aws iotwireless get-wireless-gateway-task \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "WirelessGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "WirelessGatewayTaskDefinitionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "Status": "Success"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.