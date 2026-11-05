**To list the wireless gateway task definitions**

The following ``list-wireless-gateway-task-definitions`` example lists the available wireless gateway task definitions registered to your AWS account. ::

    aws iotwireless list-wireless-gateway-task-definitions

Output::

    {
        "TaskDefinitions": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "LoRaWAN" :
                    {
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
        ]
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.