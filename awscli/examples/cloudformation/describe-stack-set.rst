**To get information about a stack set**

The following ``describe-stack-set`` example displays details about the specified stack set. ::

    aws cloudformation describe-stack-set \
        --stack-set-name my-stack-set

Output::

    {
        "StackSet": {
            "StackSetName": "my-stack-set",
            "StackSetId": "my-stack-set:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Description": "Create an Amazon SNS topic",
            "Status": "ACTIVE",
            "TemplateBody": "AWSTemplateFormatVersion: '2010-09-09'\nDescription: An AWS SNS topic\nResources:\n  topic:\n    Type: AWS::SNS::Topic",
            "Parameters": [],
            "Capabilities": [],
            "Tags": [],
            "StackSetARN": "arn:aws:cloudformation:us-west-2:123456789012:stackset/enable-config:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "AdministrationRoleARN": "arn:aws:iam::123456789012:role/AWSCloudFormationStackSetAdministrationRole",
            "ExecutionRoleName": "AWSCloudFormationStackSetExecutionRole"
        }
    }

For more information, see `Managing stacks across accounts and Regions with StackSets <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html>`__ in the *AWS CloudFormation User Guide*.
