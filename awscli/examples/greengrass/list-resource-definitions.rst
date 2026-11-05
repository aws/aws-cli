**To list the resources that are defined**

The following ``list-resource-definitions`` example lists the resources that are defined for AWS IoT Greengrass to use. ::

    aws greengrass list-resource-definitions
    
Output::

    {
        "Definitions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreationTimestamp": "2019-06-19T16:40:59.261Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LastUpdatedTimestamp": "2019-06-19T16:40:59.261Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2019-06-19T21:51:28.212Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "LastUpdatedTimestamp": "2019-06-19T21:51:28.212Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Name": "MyGreengrassResources"
            }
        ]
    }

For more information, see `Access local resources with Lambda functions and connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/access-local-resources.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
