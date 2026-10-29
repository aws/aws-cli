**To get information about a stack resource**

The following ``describe-stack-resources`` example displays details for the resources in the specified stack. ::

    aws cloudformation describe-stack-resources \
        --stack-name my-stack

Output::

    {
        "StackResources": [
            {
                "StackName": "my-stack",
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LogicalResourceId": "bucket",
                "PhysicalResourceId": "my-stack-bucket-1vc62xmplgguf",
                "ResourceType": "AWS::S3::Bucket",
                "Timestamp": "2019-10-02T04:34:11.345Z",
                "ResourceStatus": "CREATE_COMPLETE",
                "DriftInformation": {
                    "StackResourceDriftStatus": "IN_SYNC"
                }
            },
            {
                "StackName": "my-stack",
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LogicalResourceId": "function",
                "PhysicalResourceId": "my-function-SEZV4XMPL4S5",
                "ResourceType": "AWS::Lambda::Function",
                "Timestamp": "2019-10-02T05:34:27.989Z",
                "ResourceStatus": "UPDATE_COMPLETE",
                "DriftInformation": {
                    "StackResourceDriftStatus": "IN_SYNC"
                }
            },
            {
                "StackName": "my-stack",
                "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LogicalResourceId": "functionRole",
                "PhysicalResourceId": "my-functionRole-HIZXMPLEOM9E",
                "ResourceType": "AWS::IAM::Role",
                "Timestamp": "2019-10-02T04:34:06.350Z",
                "ResourceStatus": "CREATE_COMPLETE",
                "DriftInformation": {
                    "StackResourceDriftStatus": "IN_SYNC"
                }
            }
        ]
    }

For more information, see `Managing AWS resources as a single unit with CloudFormation stacks <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacks.html>`__ in the *AWS CloudFormation User Guide*.
