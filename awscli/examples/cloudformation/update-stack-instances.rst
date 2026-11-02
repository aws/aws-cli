**To update stack instances**

The following ``update-stack-instances`` example retries an update on stack instances in two accounts in two regions with the most recent settings. The specified fault tolerance setting ensures that the update is attempted in all accounts and regions, even if some stacks cannot be updated. ::

    aws cloudformation update-stack-instances \
        --stack-set-name my-stack-set \
        --accounts 123456789012 123456789111 \
        --regions us-east-1 us-west-2 \
        --operation-preferences FailureToleranceCount=3

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Update CloudFormation StackSets <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-update.html>`__ in the *AWS CloudFormation User Guide*.
