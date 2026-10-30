**To list the tags assigned to the resource**

The following ``list-tags-for-resource`` example lists the tags assigned to a wireless destination resource. ::

    aws iotwireless list-tags-for-resource \
        --resource-arn "arn:aws:iotwireless:us-west-2:123456789012:Destination/IoTWirelessDestination"

Output::

    {
        "Tags": [
            {
                "Value": "MyValue", 
                "Key": "MyTag"
            }
        ]
    }

For more information, see `Tagging your AWS IoT Wireless resources <https://docs.aws.amazon.com/iot-wireless/latest/developerguide/tagging-iotwireless.html>`__ in the *AWS IoT Developers Guide*.
