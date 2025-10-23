**To list actions for a stack refactor operation**

The following ``list-stack-refactor-actions`` example lists actions for the stack refactor operation with the specified stack refactor ID. ::

    aws cloudformation list-stack-refactor-actions \
        --stack-refactor-id 9c384f70-4e07-4ed7-a65d-fee5eb430841

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
                        "StackName": "arn:aws:cloudformation:us-east-1:123456789012:stack/Stack1/3e6a1ff0-94b1-11f0-aa6f-0a88d2e03acf",
                        "LogicalResourceId": "MyLambdaRole"
                    },
                    "Destination": {
                        "StackName": "arn:aws:cloudformation:us-east-1:123456789012:stack/Stack2/5da91650-94b1-11f0-81cf-0a23500e151b",
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
                        "Value": "arn:aws:cloudformation:us-east-1:123456789012:stack/Stack2/5da91650-94b1-11f0-81cf-0a23500e151b"
                    }
                ],
                "UntagResources": [
                    "aws:cloudformation:stack-name",
                    "aws:cloudformation:logical-id",
                    "aws:cloudformation:stack-id"
                ],
                "ResourceMapping": {
                    "Source": {
                        "StackName": "arn:aws:cloudformation:us-east-1:123456789012:stack/Stack1/3e6a1ff0-94b1-11f0-aa6f-0a88d2e03acf",
                        "LogicalResourceId": "MyFunction"
                    },
                    "Destination": {
                        "StackName": "arn:aws:cloudformation:us-east-1:123456789012:stack/Stack2/5da91650-94b1-11f0-81cf-0a23500e151b",
                        "LogicalResourceId": "MyFunction"
                    }
                }
            }
        ]
    }


For more information, see `Stack refactoring <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stack-refactoring.html>`__ in the *AWS CloudFormation User Guide*.
