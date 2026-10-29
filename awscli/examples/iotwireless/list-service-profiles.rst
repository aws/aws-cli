**To list the service profiles**

The following ``list-service-profiles`` example lists the available service profiles registered to your AWS account. ::

    aws iotwireless list-service-profiles

Output::

    {
        "ServiceProfileList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "Arn": "arn:aws:iotwireless:us-west-2:123456789012:ServiceProfile/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }, 
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", 
                "Arn": "arn:aws:iotwireless:us-west-2:123456789012:ServiceProfile/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `Add profiles to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan-define-profiles.html>`__ in the *AWS IoT Developers Guide*.
