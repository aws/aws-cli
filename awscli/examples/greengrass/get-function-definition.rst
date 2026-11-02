**To retrieve a function definition**

The following ``get-function-definition`` example displays details for the specified function definition. To retrieve the IDs of your function definitions, use the ``list-function-definitions`` command. ::

    aws greengrass get-function-definition \
        --function-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-18T16:21:21.431Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-18T16:21:21.431Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "tags": {}
    }

For more information, see `Run Lambda functions on the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/lambda-functions.html>`__ in the *AWS IoT Greengrass Developer Guide*.
