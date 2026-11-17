**To list the versions of a Lambda function**

The following ``list-function-definition-versions`` example lists all of the versions of the specified Lambda function. You can use the ``list-function-definitions`` command to get the ID. ::

    aws greengrass list-function-definition-versions \
        --function-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Versions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreationTimestamp": "2019-06-18T17:04:30.776Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2019-06-18T17:02:44.087Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "CreationTimestamp": "2019-06-18T17:01:42.284Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "CreationTimestamp": "2019-06-18T16:21:21.431Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555"
            }
        ]
    }

For more information, see `Run Lambda functions on the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/lambda-functions.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
