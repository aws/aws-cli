**To get information about a service profile**

The following ``get-service-profile`` example gets information about the service profile with the specified ID that you created. ::

    aws iotwireless get-service-profile \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" 

Output::

    {
        "Arn": "arn:aws:iotwireless:us-west-2:123456789012:ServiceProfile/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
        "LoRaWAN": {
            "HrAllowed": false, 
            "NwkGeoLoc": false, 
            "DrMax": 15, 
            "UlBucketSize": 4096, 
            "PrAllowed": false, 
            "ReportDevStatusBattery": false, 
            "DrMin": 0, 
            "DlRate": 60, 
            "AddGwMetadata": false, 
            "ReportDevStatusMargin": false, 
            "MinGwDiversity": 1, 
            "RaAllowed": false, 
            "DlBucketSize": 4096, 
            "DevStatusReqFreq": 24, 
            "TargetPer": 5, 
            "UlRate": 60
        }
    }

For more information, see `Add profiles to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan-define-profiles.html>`__ in the *AWS IoT Developers Guide*.
