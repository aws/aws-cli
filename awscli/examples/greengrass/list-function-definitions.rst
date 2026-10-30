**To list Lambda functions**

The following ``list-function-definitions`` example lists all of the Lambda functions defined for your AWS account. ::

    aws greengrass list-function-definitions

Output::

    {
        "Definitions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreationTimestamp": "2018-10-17T04:30:32.884Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LastUpdatedTimestamp": "2018-10-17T04:30:32.884Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2019-06-18T16:21:21.431Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "LastUpdatedTimestamp": "2019-06-18T16:21:21.431Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "CreationTimestamp": "2019-06-18T16:24:16.123Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "LastUpdatedTimestamp": "2019-06-18T16:24:16.123Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
                "CreationTimestamp": "2019-06-18T16:14:17.784Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
                "LastUpdatedTimestamp": "2019-06-18T16:14:17.784Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE88888",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE77777/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE88888"
            }
        ]
    }

For more information, see `Run Lambda functions on the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/lambda-functions.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
