**To create an alias for a Lambda function**

The following ``create-alias`` example creates an alias named ``LIVE`` that points to version 1 of the ``my-function`` Lambda function. ::

    aws lambda create-alias \
        --function-name my-function \
        --description "alias for live version of function" \
        --function-version 1 \
        --name LIVE

Output::

    {
        "FunctionVersion": "1",
        "Name": "LIVE",
        "AliasArn": "arn:aws:lambda:us-west-2:123456789012:function:my-function:LIVE",
        "RevisionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Description": "alias for live version of function"
    }

For more information, see `Configuring AWS Lambda Function Aliases <https://docs.aws.amazon.com/lambda/latest/dg/aliases-intro.html>`__ in the *AWS Lambda Developer Guide*.
