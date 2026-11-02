**To list the available wireless devices**

The following ``list-wireless-devices`` example lists the available wireless devices registered to your AWS account. ::

    aws iotwireless list-wireless-devices

Output::

    {
        "WirelessDeviceList": [
            {
                "Name": "myLoRaWANDevice", 
                "DestinationName": "IoTWirelessDestination", 
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "Type": "LoRaWAN", 
                "LoRaWAN": {
                    "DevEui": "ac12efc654d23fc2"
                }, 
                "Arn": "arn:aws:iotwireless:us-west-2:123456789012:WirelessDevice/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.
