**To list Greengrass core definitions**

The following ``list-core-definitions`` example lists all of the Greengrass core definitions for your AWS account. ::

    aws greengrass list-core-definitions
    
Output::

    {
        "Definitions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreationTimestamp": "2018-10-17T04:30:32.786Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LastUpdatedTimestamp": "2018-10-17T04:30:32.786Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2019-06-18T16:24:16.064Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "LastUpdatedTimestamp": "2019-06-18T16:24:16.064Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "CreationTimestamp": "2019-06-18T16:21:21.351Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "LastUpdatedTimestamp": "2019-06-18T16:21:21.351Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
                "CreationTimestamp": "2019-06-18T16:14:17.709Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
                "LastUpdatedTimestamp": "2019-06-18T16:14:17.709Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE88888",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE77777/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE88888"
            }
        ]
    }

For more information, see `Configure the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-core.html>`__ in the *AWS IoT Greengrass Developer Guide*.
