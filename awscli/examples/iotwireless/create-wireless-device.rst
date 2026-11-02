**To create an IoT wireless device**

The following ``create-wireless-device`` example creates a wireless device resource of the type LoRaWAN. ::

    aws iotwireless create-wireless-device \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "Description": "My LoRaWAN wireless device"
        "DestinationName": "IoTWirelessDestination"
        "LoRaWAN": {
            "DeviceProfileId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "ServiceProfileId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "OtaaV1_1": {
                "AppKey": "3f4ca100e2fc675ea123f4eb12c4a012",
                "JoinEui": "b4c231a359bc2e3d",
                "NwkKey": "01c3f004a2d6efffe32c4eda14bcd2b4"
            },
            "DevEui": "ac12efc654d23fc2"
        },
        "Name": "SampleIoTWirelessThing"
        "Type": LoRaWAN
    }

Output::

    {
        "Arn": "arn:aws:iotwireless:us-west-2:123456789012:WirelessDevice/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.