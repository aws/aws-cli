**Example 1: To invoke a Lambda function synchronously**

The following ``invoke`` example invokes the ``my-function`` function synchronously. ::

    aws lambda invoke \
        --function-name my-function \
        --payload '{ "name": "Bob" }' \
        response.json

Output::

    {
        "ExecutedVersion": "$LATEST",
        "StatusCode": 200
    }

For more information, see `Synchronous Invocation <https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html>`__ in the *AWS Lambda Developer Guide*.

**Example 2: To invoke a Lambda function asynchronously**

The following ``invoke`` example invokes the ``my-function`` function asynchronously. ::

    aws lambda invoke \
        --function-name my-function \
        --invocation-type Event \
        --payload '{ "name": "Bob" }' \
        response.json

Output::

    {
        "StatusCode": 202
    }

For more information, see `Asynchronous Invocation <https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html>`__ in the *AWS Lambda Developer Guide*.
