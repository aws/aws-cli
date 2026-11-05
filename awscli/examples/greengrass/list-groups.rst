**To list the Greengrass groups**

The following ``list-groups`` example lists all Greengrass groups that are defined in your AWS account. ::

    aws greengrass list-groups

Output::

    {
        "Groups": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreationTimestamp": "2019-06-18T16:21:21.457Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LastUpdatedTimestamp": "2019-06-18T16:21:21.457Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "GGGroup4Pi3"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2018-10-31T21:52:46.603Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "LastUpdatedTimestamp": "2018-10-31T21:52:46.603Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Name": "MyTestGroup"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "CreationTimestamp": "2018-12-31T21:39:36.771Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "LastUpdatedTimestamp": "2018-12-31T21:39:36.771Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "Name": "smp-ggrass-group"
            }
        ]
    }

For more information, see `Overview of the AWS IoT Greengrass group object model <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
