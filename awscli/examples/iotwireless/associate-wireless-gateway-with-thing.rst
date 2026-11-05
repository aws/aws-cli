**To associate a thing to a wireless gateway**

The following ``associate-wireless-gateway-with-thing`` example associates a thing to a wireless gateway. ::

    aws iotwireless associate-wireless-gateway-with-thing \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --thing-arn "arn:aws:iot:us-west-2:123456789012:thing/MyIoTWirelessThing"

This command produces no output.

For more information, see `Add your gateways and wireless devices to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan-onboard-devices.html>`__ in the *AWS IoT Developers Guide*.