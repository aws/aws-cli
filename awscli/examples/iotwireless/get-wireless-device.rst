**To get information about the wireless device**

The following ``get-wireless-device`` example lists the available widgets in your AWS account. ::

    aws iotwireless get-wireless-device \
        --identifier "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --identifier-type WirelessDeviceID

Output::

    {
        "Name": "myLoRaWANDevice", 
        "ThingArn": "arn:aws:iot:us-west-2:123456789012:thing/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
        "DestinationName": "IoTWirelessDestination", 
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "ThingName": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
        "Type": "LoRaWAN", 
        "LoRaWAN": {
            "DeviceProfileId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333", 
            "ServiceProfileId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444", 
            "OtaaV1_1": {
                "AppKey": "3f4ca100e2fc675ea123f4eb12c4a012", 
                "JoinEui": "b4c231a359bc2e3d", 
                "NwkKey": "01c3f004a2d6efffe32c4eda14bcd2b4"
            }, 
            "DevEui": "ac12efc654d23fc2"
        }, 
        "Arn": "arn:aws:iotwireless:us-west-2:123456789012:WirelessDevice/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "Description": "My LoRaWAN wireless device"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.
