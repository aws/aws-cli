**To send data to the wireless device**

The following ``send-data-to-wireless-device`` example sends a decrypted application data frame to the wireless device. ::

    aws iotwireless send-data-to-wireless-device \
        --id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --transmit-mode "1" \
        --payload-data "SGVsbG8gVG8gRGV2c2lt" \
        --wireless-metadata LoRaWAN={FPort=1}

Output::

    {
        "MessageId": "6011dd36-0043d6eb-0072-0008"
    }

For more information, see `Connecting devices and gateways to AWS IoT Core for LoRaWAN <https://docs.aws.amazon.com/iot/latest/developerguide/connect-iot-lorawan.html>`__ in the *AWS IoT Developers Guide*.