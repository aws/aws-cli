**To get information about a wireless gateway**

The following ``get-wireless-gateway`` example gets information about the wireless gateway ``myFirstLoRaWANGateway``. ::

    aws iotwireless get-wireless-gateway \
        --identifier "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --identifier-type WirelessGatewayId 

Output::

    {
        "Description": "My first LoRaWAN gateway", 
        "ThingArn": "arn:aws:iot:us-west-2:123456789012:thing/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
        "LoRaWAN": {
            "RfRegion": "US915", 
            "GatewayEui": "a1b2c3d4567890ab"
        }, 
        "ThingName": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "Arn": "arn:aws:iotwireless:us-west-2:123456789012:WirelessGateway/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "Name": "myFirstLoRaWANGateway"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.
