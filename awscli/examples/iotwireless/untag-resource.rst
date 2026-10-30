**To remove one or more tags from a resource**

The following ``untag-resource`` example removes the tag ``MyTag`` and its value from the wireless destination ``IoTWirelessDestination``. ::

    aws iotwireless untag-resource \
        --resource-arn "arn:aws:iotwireless:us-west-2:123456789012:Destination/IoTWirelessDestination" \
        --tag-keys "MyTag"

This command produces no output.

For more information, see `Tagging your AWS IoT Wireless resources <https://docs.aws.amazon.com/iot-wireless/latest/developerguide/tagging-iotwireless.html>`__ in the *AWS IoT Developers Guide*.