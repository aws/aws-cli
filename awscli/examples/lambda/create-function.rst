**To create a Lambda function**

The following ``create-function`` example creates a Lambda function named ``my-function``. ::

    aws lambda create-function \
        --function-name my-function \
        --runtime nodejs22.x \
        --zip-file fileb://my-function.zip \
        --handler my-function.handler \
        --role arn:aws:iam::123456789012:role/service-role/MyTestFunction-role-tges6bf4

Contents of ``my-function.zip``::

    This file is a deployment package that contains your function code and any dependencies.

Output::

    {
        "TracingConfig": {
            "Mode": "PassThrough"
        },
        "CodeSha256": "PFn4S+er27qk+UuZSTKEQfNKG/XNn7QJs90mJgq6oH8=",
        "FunctionName": "my-function",
        "CodeSize": 308,
        "RevisionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "MemorySize": 128,
        "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:my-function",
        "Version": "$LATEST",
        "Role": "arn:aws:iam::123456789012:role/service-role/MyTestFunction-role-zgur6bf4",
        "Timeout": 3,
        "LastModified": "2025-10-14T22:26:11.234+0000",
        "Handler": "my-function.handler",
        "Runtime": "nodejs22.x",
        "Description": ""
    }

For more information, see `Configure Lambda function memory <https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html>`__ in the *AWS Lambda Developer Guide*.
