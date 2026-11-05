**To list the versions of a device definition**

The following ``list-device-definition-versions`` example displays the device definition versions associated with the specified device definition. ::

    aws greengrass list-device-definition-versions \
        --device-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Versions": [
            {
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreationTimestamp": "2019-09-11T00:15:09.838Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2019-09-11T00:11:06.197Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            }
        ]
    }

For more information, see `Overview of the AWS IoT Greengrass group object model <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
