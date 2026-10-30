**To retrieve details about a specific version of a Lambda function**

The following ``get-function-definition-version`` example retrieves information about the specified version of the specified function definition. To retrieve the IDs of all versions of the function definition, use the ``list-function-definition-versions`` command. To retrieve the ID of the last version added to the function definition, use the ``get-function-definition`` command and check the ``LatestVersion`` property. ::

    aws greengrass get-function-definition-version \
        --function-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --function-definition-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-18T17:04:30.776Z",
        "Definition": {
            "Functions": [
                {
                    "FunctionArn": "arn:aws:lambda:::function:GGIPDetector:1",
                    "FunctionConfiguration": {
                        "Environment": {},
                        "MemorySize": 32768,
                        "Pinned": true,
                        "Timeout": 3
                    },
                    "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
                },
                {
                    "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:Greengrass_HelloWorld:GG_HelloWorld",
                    "FunctionConfiguration": {
                        "EncodingType": "json",
                        "Environment": {
                            "Variables": {}
                        },
                        "MemorySize": 16384,
                        "Pinned": true,
                        "Timeout": 25
                    },
                    "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
                }
            ]
        },
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Run Lambda functions on the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/lambda-functions.html>`__ in the *AWS IoT Greengrass Developer Guide*.
