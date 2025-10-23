**To describe a stack refactor operation**

The following ``describe-stack-refactor`` example describes the stack refactor operation with the specified stack refactor ID. ::

    aws cloudformation describe-stack-refactor \
        --stack-refactor-id 9c384f70-4e07-4ed7-a65d-fee5eb430841

Output::

    {
        "StackRefactorId": "9c384f70-4e07-4ed7-a65d-fee5eb430841",
        "StackIds": [
            "arn:aws:cloudformation:us-east-1:123456789012:stack/Stack1/3e6a1ff0-94b1-11f0-aa6f-0a88d2e03acf",
            "arn:aws:cloudformation:us-east-1:123456789012:stack/Stack2/5da91650-94b1-11f0-81cf-0a23500e151b"
        ],
        "ExecutionStatus": "AVAILABLE",
        "Status": "CREATE_COMPLETE"
    }

For more information, see `Stack refactoring <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stack-refactoring.html>`__ in the *AWS CloudFormation User Guide*.
