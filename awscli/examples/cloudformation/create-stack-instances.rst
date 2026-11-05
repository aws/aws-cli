**To create stack instances**

The following ``create-stack-instances`` example creates instances of a stack set in two accounts and in four regions. The fault tolerance setting ensures that the update is attempted in all accounts and regions, even if some stacks cannot be created. ::

    aws cloudformation create-stack-instances \
        --stack-set-name my-stack-set \
        --accounts 123456789012 123456789111 \
        --regions us-east-1 us-east-2 us-west-1 us-west-2 \
        --operation-preferences FailureToleranceCount=7

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

To create a stack set, use the ``create-stack-set`` command.

For more information, see `Add stacks to CloudFormation StackSets <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stackinstances-create.html>`__ in the *AWS CloudFormation User Guide*.
