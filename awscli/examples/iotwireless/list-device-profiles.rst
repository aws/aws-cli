**To list the device profiles**

The following ``list-device-profiles`` example lists the available device profiles registered to your AWS account. ::

    aws iotwireless list-device-profiles 

Output::

    {
        "DeviceProfileList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "Arn": "arn:aws:iotwireless:us-west-2:123456789012:DeviceProfile/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }, 
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
                "Arn": "arn:aws:iotwireless:us-west-2:123456789012:DeviceProfile/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `Add profiles to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan-define-profiles.html>`__ in the *AWS IoT Developers Guide*.
