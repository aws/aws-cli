**To view a provisioned concurrency configuration**

The following ``get-provisioned-concurrency-config`` example displays details for the provisioned concurrency configuration for the ``BLUE`` alias of the specified function. ::

    aws lambda get-provisioned-concurrency-config \
        --function-name my-function \
        --qualifier BLUE

Output::

    {
        "RequestedProvisionedConcurrentExecutions": 100,
        "AvailableProvisionedConcurrentExecutions": 100,
        "AllocatedProvisionedConcurrentExecutions": 100,
        "Status": "READY",
        "LastModified": "2019-12-31T20:28:49+0000"
    }

For more information, see `Configuring provisioned concurrency for an Event Function <https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html>`__ in the *AWS Lambda Developer Guide*.
