**To describe stack events**

The following ``describe-stack-events`` example displays the 2 most recent events for the specified stack. ::

    aws cloudformation describe-stack-events \
        --stack-name my-stack \
        --max-items 2

Output::

    {
        "StackEvents": [
            {
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "EventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "StackName": "my-stack",
                "LogicalResourceId": "my-stack",
                "PhysicalResourceId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ResourceType": "AWS::CloudFormation::Stack",
                "Timestamp": "2019-10-02T05:34:29.556Z",
                "ResourceStatus": "UPDATE_COMPLETE"
            },
            {
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "EventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "StackName": "my-stack",
                "LogicalResourceId": "my-stack",
                "PhysicalResourceId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ResourceType": "AWS::CloudFormation::Stack",
                "Timestamp": "2019-10-02T05:34:29.127Z",
                "ResourceStatus": "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS"
            }
        ],
        "NextToken": "eyJOZXh0VG9XMPLiOiBudWxsLCAiYm90b190cnVuY2F0ZV9hbW91bnQiOiAyfQ=="
    }

For more information, see `Monitor stack progress <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/monitor-stack-progress.html>`__ in the *AWS CloudFormation User Guide*.
