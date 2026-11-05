**To get firmware information about a wireless gateway**

The following ``get-wireless-gateway-firmware-information`` example gets firmware version and other information about a wireless gateway. ::

    aws iotwireless get-wireless-gateway-firmware-information \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"


Output::

    {
        "LoRaWAN" :{
            "CurrentVersion" :{
                "PackageVersion" : "1.0.0",
                "Station" : "2.0.5",
                "Model" : "linux"
            }
        }
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.
