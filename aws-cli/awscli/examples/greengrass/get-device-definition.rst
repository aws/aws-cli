**To get a device definition**

The following ``get-device-definition`` example retrieves information about the specified device definition. To retrieve the IDs of your device definitions, use the ``list-device-definitions`` command. ::

    aws greengrass get-device-definition \
        --device-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Name": "TemperatureSensors",
        "tags": {},
        "LastUpdatedTimestamp": "2019-09-11T00:19:03.698Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-09-11T00:11:06.197Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Create client devices in an AWS IoT Greengrass group <https://docs.aws.amazon.com/greengrass/v1/developerguide/device-group.html>`__ in the *AWS IoT Greengrass Developer Guide*.
