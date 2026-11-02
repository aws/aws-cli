**To describe a stack refactor operation**

The following ``describe-stack-refactor`` example describes the stack refactor operation with the specified stack refactor ID. ::

    aws cloudformation describe-stack-refactor \
        --stack-refactor-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "StackRefactorId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "StackIds": [
            "arn:aws:cloudformation:us-west-2:123456789012:stack/Stack1/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "arn:aws:cloudformation:us-west-2:123456789012:stack/Stack2/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
        ],
        "ExecutionStatus": "AVAILABLE",
        "Status": "CREATE_COMPLETE"
    }

For more information, see `Stack refactoring <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stack-refactoring.html>`__ in the *AWS CloudFormation User Guide*.
