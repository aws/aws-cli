**To list the versions of a Greengrass group**

The following ``list-group-versions`` example lists the versions of the specified Greengrass group. ::

    aws greengrass list-group-versions \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Versions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreationTimestamp": "2019-06-18T17:04:30.915Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2019-06-18T17:03:52.663Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "CreationTimestamp": "2019-06-18T17:02:44.189Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "CreationTimestamp": "2019-06-18T17:01:42.401Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "CreationTimestamp": "2019-06-18T16:21:21.457Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
            }
        ]
    }

For more information, see `Overview of the AWS IoT Greengrass group object model <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
