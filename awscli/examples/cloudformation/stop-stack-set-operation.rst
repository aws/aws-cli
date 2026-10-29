**To stop a stack set operation**

The following ``stop-stack-set-operation`` example stops an in-progess update operation on the specified stack set. ::

    aws cloudformation stop-stack-set-operation \
        --stack-set-name my-stack-set \
        --operation-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `StackSets concepts <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html>`__ in the *AWS CloudFormation User Guide*.
