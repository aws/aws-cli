**To get information about a device profile**

The following ``get-device-profile`` example gets information about the device profile with the specified ID that you created. ::

    aws iotwireless get-device-profile \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" 

Output::

    {
        "Arn": "arn:aws:iotwireless:us-west-2:123456789012:DeviceProfile/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "LoRaWAN": {
        "MacVersion": "1.0.3", 
        "MaxDutyCycle": 10, 
        "Supports32BitFCnt": false, 
        "RegParamsRevision": "RP002-1.0.1", 
        "SupportsJoin": true, 
        "RfRegion": "US915", 
        "MaxEirp": 13, 
        "SupportsClassB": false, 
        "SupportsClassC": false
        }
    }

For more information, see `Add profiles to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan-define-profiles.html>`__ in the *AWS IoT Developers Guide*.
