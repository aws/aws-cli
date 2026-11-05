**To list your device definitions**

The following ``list-device-definitions`` example displays details about the device definitions in your AWS account in the current AWS Region. ::

    aws greengrass list-device-definitions

Output::

    {
        "Definitions": [
            {
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "LastUpdatedTimestamp": "2019-06-14T15:42:09.059Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreationTimestamp": "2019-06-14T15:42:09.059Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Name": "TestDeviceDefinition",
                "LastUpdatedTimestamp": "2019-04-16T23:17:43.245Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "CreationTimestamp": "2019-04-16T23:17:43.245Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            },
            {
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "Name": "TemperatureSensors",
                "LastUpdatedTimestamp": "2019-09-10T00:19:03.698Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "CreationTimestamp": "2019-09-11T00:11:06.197Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555"
            }
        ]
    }

For more information, see `Overview of the AWS IoT Greengrass group object model <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
