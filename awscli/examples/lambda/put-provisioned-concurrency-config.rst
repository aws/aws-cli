**To allocate provisioned concurrency**

The following ``put-provisioned-concurrency-config`` example allocates 100 provisioned concurrency for the ``BLUE`` alias of the specified function. ::

    aws lambda put-provisioned-concurrency-config \
        --function-name my-function \
        --qualifier BLUE \
        --provisioned-concurrent-executions 100

Output::

    {
        "RequestedProvisionedConcurrentExecutions": 100,
        "AllocatedProvisionedConcurrentExecutions": 0,
        "Status": "IN_PROGRESS",
        "LastModified": "2019-11-21T19:32:12+0000"
    }

For more information, see `Configuring provisioned concurrency for an Event Function <https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html>`__ in the *AWS Lambda Developer Guide*.
