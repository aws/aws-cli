**To get information about a stack resource**

The following ``describe-stack-resource`` example displays details for the resource named ``MyFunction`` in the specified stack. ::

    aws cloudformation describe-stack-resource \
        --stack-name MyStack \
        --logical-resource-id MyFunction

Output::

    {
        "StackResourceDetail": {
            "StackName": "MyStack",
            "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/MyStack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "LogicalResourceId": "MyFunction",
            "PhysicalResourceId": "my-function-SEZV4XMPL4S5",
            "ResourceType": "AWS::Lambda::Function",
            "LastUpdatedTimestamp": "2019-10-02T05:34:27.989Z",
            "ResourceStatus": "UPDATE_COMPLETE",
            "Metadata": "{}",
            "DriftInformation": {
                "StackResourceDriftStatus": "IN_SYNC"
            }
        }
    }

For more information, see `Managing AWS resources as a single unit with CloudFormation stacks <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacks.html>`__ in the *AWS CloudFormation User Guide*.
