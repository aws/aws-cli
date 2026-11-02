**To specify a tag key and value for a resource**

The following ``tag-resource`` example tags the wireless destination ``IoTWirelessDestination`` with the key ``MyTag`` and value ``MyValue``. ::

    aws iotwireless tag-resource \
        --resource-arn "arn:aws:iotwireless:us-west-2:123456789012:Destination/IoTWirelessDestination" \
        --tags Key="MyTag",Value="MyValue" 

This command produces no output.

For more information, see `Tagging your AWS IoT Wireless resources <https://docs.aws.amazon.com/iot-wireless/latest/developerguide/tagging-iotwireless.html>`__ in the *AWS IoT Developers Guide*.