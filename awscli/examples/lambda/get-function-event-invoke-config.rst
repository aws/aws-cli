**To view an asynchronous invocation configuration**

The following ``get-function-event-invoke-config`` example retrieves the asynchronous invocation configuration for the ``BLUE`` alias of the specified function. ::

    aws lambda get-function-event-invoke-config \
        --function-name my-function:BLUE

Output::

    {
        "LastModified": 1577824396.653,
        "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:my-function:BLUE",
        "MaximumRetryAttempts": 0,
        "MaximumEventAgeInSeconds": 3600,
        "DestinationConfig": {
            "OnSuccess": {},
            "OnFailure": {
                "Destination": "arn:aws:sqs:us-west-2:123456789012:failed-invocations"
            }
        }
    }

For more information, see `Configuring error handling settings for Lambda asynchronous invocations <https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-configuring.html>`__ in the *AWS Lambda Developer Guide*.
