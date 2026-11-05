**To get information about a wireless gateway task definition**

The following ``get-wireless-gateway-task-definition`` example gets information about the wireless task definition with the specified ID. ::

    aws iotwireless get-wireless-gateway-task-definition \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "AutoCreateTasks": true,
        "Name": "TestAutoUpdate",
        "Update":{
            "UpdateDataSource" : "s3://amzn-s3-demo-bucket/station",
            "UpdateDataRole" : "arn:aws:iam::123456789012:role/SDK_Test_Role",
            "LoRaWAN" :{
                "CurrentVersion" :{
                    "PackageVersion" : "1.0.0",
                    "Station" : "2.0.5",
                    "Model" : "linux"
                },
                "UpdateVersion" :{
                    "PackageVersion" : "1.0.1",
                    "Station" : "2.0.5",
                    "Model" : "minihub"
                }
            }
        }
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.