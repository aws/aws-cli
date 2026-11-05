**To delete an asynchronous invocation configuration**

The following ``delete-function-event-invoke-config`` example deletes the asynchronous invocation configuration for the ``GREEN`` alias of the specified function. ::

    aws lambda delete-function-event-invoke-config \
        --function-name my-function:GREEN

This command produces no output.

For more information, see `Configuring error handling settings for Lambda asynchronous invocations <https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-configuring.html>`__ in the *AWS Lambda Developer Guide*.
