**To list actions for a stack refactor operation**

The following ``list-stack-refactor-actions`` example lists actions for the stack refactor operation with the specified stack refactor ID. ::

    aws cloudformation list-stack-refactor-actions \
        --stack-refactor-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "StackRefactorActions": [
            {
                "Action": "MOVE",
                "Entity": "RESOURCE",
                "PhysicalResourceId": "MyTestLambdaRole",
                "Description": "No configuration changes detected.",
                "Detection": "AUTO",
                "TagResources": [],
                "UntagResources": [],
                "ResourceMapping": {
                    "Source": {
                        "StackName": "arn:aws:cloudformation:us-west-2:123456789012:stack/Stack1/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                        "LogicalResourceId": "MyLambdaRole"
                    },
                    "Destination": {
                        "StackName": "arn:aws:cloudformation:us-west-2:123456789012:stack/Stack2/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                        "LogicalResourceId": "MyLambdaRole"
                    }
                }
            },
            {
                "Action": "MOVE",
                "Entity": "RESOURCE",
                "PhysicalResourceId": "MyTestFunction",
                "Description": "Resource configuration changes will be validated during refactor execution.",
                "Detection": "AUTO",
                "TagResources": [
                    {
                        "Key": "aws:cloudformation:stack-name",
                        "Value": "Stack2"
                    },
                    {
                        "Key": "aws:cloudformation:logical-id",
                        "Value": "MyFunction"
                    },
                    {
                        "Key": "aws:cloudformation:stack-id",
                        "Value": "arn:aws:cloudformation:us-west-2:123456789012:stack/Stack2/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
                    }
                ],
                "UntagResources": [
                    "aws:cloudformation:stack-name",
                    "aws:cloudformation:logical-id",
                    "aws:cloudformation:stack-id"
                ],
                "ResourceMapping": {
                    "Source": {
                        "StackName": "arn:aws:cloudformation:us-west-2:123456789012:stack/Stack1/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                        "LogicalResourceId": "MyFunction"
                    },
                    "Destination": {
                        "StackName": "arn:aws:cloudformation:us-west-2:123456789012:stack/Stack2/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                        "LogicalResourceId": "MyFunction"
                    }
                }
            }
        ]
    }


For more information, see `Stack refactoring <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stack-refactoring.html>`__ in the *AWS CloudFormation User Guide*.
