**To create the task for a wireless gateway**

The following ``create-wireless-gateway-task`` example creates a task for a wireless gateway. ::

    aws iotwireless create-wireless-gateway-task \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --wireless-gateway-task-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "WirelessGatewayTaskDefinitionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Status": "Success"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.