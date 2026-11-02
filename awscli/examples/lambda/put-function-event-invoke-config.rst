**To configure error handling for asynchronous invocation**

The following ``put-function-event-invoke-config`` example sets a maximum event age of one hour and disables retries for the specified function. ::

    aws lambda put-function-event-invoke-config \
        --function-name my-function \
        --maximum-event-age-in-seconds 3600 \
        --maximum-retry-attempts 0

Output::

    {
        "LastModified": 1573686021.479,
        "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:my-function:$LATEST",
        "MaximumRetryAttempts": 0,
        "MaximumEventAgeInSeconds": 3600,
        "DestinationConfig": {
            "OnSuccess": {},
            "OnFailure": {}
        }
    }

For more information, see `Configuring error handling settings for Lambda asynchronous invocations <https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-configuring.html>`__ in the *AWS Lambda Developer Guide*.
