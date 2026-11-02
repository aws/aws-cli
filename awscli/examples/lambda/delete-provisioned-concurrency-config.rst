**To delete a provisioned concurrency configuration**

The following ``delete-provisioned-concurrency-config`` example deletes the provisioned concurrency configuration for the ``GREEN`` alias of the specified function. ::

    aws lambda delete-provisioned-concurrency-config \
        --function-name my-function \
        --qualifier GREEN

This command produces no output.

For more information, see `Configuring provisioned concurrency for an Event Function <https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html>`__ in the *AWS Lambda Developer Guide*.
