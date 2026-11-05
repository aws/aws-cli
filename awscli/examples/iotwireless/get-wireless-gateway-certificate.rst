**To get the ID of a certificate associated with a wireless gateway**

The following ``get-wireless-gateway-certificate`` example gets the certificate ID associated with a wireless gateway that has the specified ID. ::

    aws iotwireless get-wireless-gateway-certificate \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "IotCertificateId": "8ea4aeae3db34c78cce75d9abd830356869ead6972997e0603e5fd032c804b6f"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.
