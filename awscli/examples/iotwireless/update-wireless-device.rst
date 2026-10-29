**To update the properties of a wireless device**

The following ``update-wireless-device`` example updates the properties of a wireless device registered to your AWS account. ::

    aws iotwireless update-wireless-device \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --destination-name IoTWirelessDestination2 \
        --description "Using my first LoRaWAN device"

This command produces no output.

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.