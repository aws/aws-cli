**To retrieve a list of versions of a function**

The following ``list-versions-by-function`` example displays the list of versions for the ``my-function`` Lambda function. ::

    aws lambda list-versions-by-function \
        --function-name my-function

Output::

    {
        "Versions": [
            {
                "TracingConfig": {
                    "Mode": "PassThrough"
                },
                "Version": "$LATEST",
                "CodeSha256": "sU0cJ2/hOZevwV/lTxCuQqK3gDZP3i8gUoqUUVRmY6E=",
                "FunctionName": "my-function",
                "VpcConfig": {
                    "SubnetIds": [],
                    "VpcId": "",
                    "SecurityGroupIds": []
                },
                "MemorySize": 256,
                "RevisionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CodeSize": 266,
                "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:my-function:$LATEST",
                "Handler": "index.handler",
                "Role": "arn:aws:iam::123456789012:role/service-role/helloWorldPython-role-uy3l9qyq",
                "Timeout": 3,
                "LastModified": "2019-10-01T16:47:28.490+0000",
                "Runtime": "nodejs10.x",
                "Description": ""
            },
            {
                "TracingConfig": {
                    "Mode": "PassThrough"
                },
                "Version": "1",
                "CodeSha256": "5tT2qgzYUHoqwR616pZ2dpkn/0J1FrzJmlKidWaaCgk=",
                "FunctionName": "my-function",
                "VpcConfig": {
                    "SubnetIds": [],
                    "VpcId": "",
                    "SecurityGroupIds": []
                },
                "MemorySize": 256,
                "RevisionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CodeSize": 304,
                "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:my-function:1",
                "Handler": "index.handler",
                "Role": "arn:aws:iam::123456789012:role/service-role/helloWorldPython-role-uy3l9qyq",
                "Timeout": 3,
                "LastModified": "2019-09-26T20:28:40.438+0000",
                "Runtime": "nodejs10.x",
                "Description": "new version"
            },
            {
                "TracingConfig": {
                    "Mode": "PassThrough"
                },
                "Version": "2",
                "CodeSha256": "sU0cJ2/hOZevwV/lTxCuQqK3gDZP3i8gUoqUUVRmY6E=",
                "FunctionName": "my-function",
                "VpcConfig": {
                    "SubnetIds": [],
                    "VpcId": "",
                    "SecurityGroupIds": []
                },
                "MemorySize": 256,
                "RevisionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CodeSize": 266,
                "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:my-function:2",
                "Handler": "index.handler",
                "Role": "arn:aws:iam::123456789012:role/service-role/helloWorldPython-role-uy3l9qyq",
                "Timeout": 3,
                "LastModified": "2019-10-01T16:47:28.490+0000",
                "Runtime": "nodejs10.x",
                "Description": "newer version"
            }
        ]
    }

For more information, see `Configuring AWS Lambda Function Aliases <https://docs.aws.amazon.com/lambda/latest/dg/aliases-intro.html>`__ in the *AWS Lambda Developer Guide*.
