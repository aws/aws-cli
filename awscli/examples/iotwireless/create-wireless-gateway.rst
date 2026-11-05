**To create a wireless gateway**

The following ``create-wireless-gateway`` example creates a wireless LoRaWAN device gateway. ::

    aws iotwireless create-wireless-gateway \
        --lorawan GatewayEui="a1b2c3d4567890ab",RfRegion="US915" \
        --name "myFirstLoRaWANGateway" \
        --description "Using my first LoRaWAN gateway"

Output::

    {
        "Arn": "arn:aws:iotwireless:us-west-2:123456789012:WirelessGateway/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.

