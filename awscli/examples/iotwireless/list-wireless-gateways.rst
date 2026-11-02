**To list the wireless gateways**

The following ``list-wireless-gateways`` example lists the available wireless gateways in your AWS account. ::

    aws iotwireless list-wireless-gateways

Output::

    {
        "WirelessGatewayList": [
            {
                "Description": "My first LoRaWAN gateway", 
                "LoRaWAN": {
                    "RfRegion": "US915", 
                    "GatewayEui": "dac632ebc01d23e4"
                }, 
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "Arn": "arn:aws:iotwireless:us-west-2:123456789012:WirelessGateway/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "Name": "myFirstLoRaWANGateway"
            }, 
            {
                "Description": "My second LoRaWAN gateway", 
                "LoRaWAN": {
                    "RfRegion": "US915", 
                    "GatewayEui": "cda123fffe92ecd2"
                }, 
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
                "Arn": "arn:aws:iotwireless:us-west-2:123456789012:WirelessGateway/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
                "Name": "mySecondLoRaWANGateway"
            }
        ]
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.
