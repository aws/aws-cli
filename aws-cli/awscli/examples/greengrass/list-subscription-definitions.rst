**To get a list subscription definitions**

The following ``list-subscription-definitions`` example lists all of the AWS IoT Greengrass subscriptions that are defined in your AWS account. ::

    aws greengrass list-subscription-definitions

Output::

    {
        "Definitions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreationTimestamp": "2019-06-18T17:03:52.392Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LastUpdatedTimestamp": "2019-06-18T17:03:52.392Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2018-10-18T15:45:34.024Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "LastUpdatedTimestamp": "2018-10-18T15:45:34.024Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "CreationTimestamp": "2018-10-22T17:09:31.429Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "LastUpdatedTimestamp": "2018-10-22T17:09:31.429Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
            }
        ]
    }

For more information, see `Overview of the AWS IoT Greengrass group object model <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
