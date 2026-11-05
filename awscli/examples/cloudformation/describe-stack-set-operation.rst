**To get information about a stack set operation**

The following ``describe-stack-set-operation`` example displays details for an update operation on the specified stack set. ::

    aws cloudformation describe-stack-set-operation \
        --stack-set-name enable-config \
        --operation-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "StackSetOperation": {
            "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "StackSetId": "enable-config:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "Action": "UPDATE",
            "Status": "SUCCEEDED",
            "OperationPreferences": {
                "RegionOrder": [
                    "us-east-1",
                    "us-west-2",
                    "eu-west-1",
                    "us-west-1"
                ],
                "FailureToleranceCount": 7,
                "MaxConcurrentCount": 2
            },
            "AdministrationRoleARN": "arn:aws:iam::123456789012:role/AWSCloudFormationStackSetAdministrationRole",
            "ExecutionRoleName": "AWSCloudFormationStackSetExecutionRole",
            "CreationTimestamp": "2019-10-03T16:28:44.377Z",
            "EndTimestamp": "2019-10-03T16:42:08.607Z"
        }
    }

For more information, see `StackSets concepts <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html>`__ in the *AWS CloudFormation User Guide*.
