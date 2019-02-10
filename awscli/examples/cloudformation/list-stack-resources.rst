**To list Resources created by an AWS CloudFormation stack**

The following ``list-stack-resources`` command shows the resources created by a stack::

  $ aws cloudformation list-stack-resources --stack-name arn:aws:cloudformation:us-east-1:<account_number>:stack/<stack_name>/<stack_guid>

Output::

    "StackResourceSummaries": [
        {
            "ResourceType": "AWS::S3::Bucket",
            "LastUpdatedTimestamp": "2019-02-06T20:28:49.358Z",
            "ResourceStatus": "CREATE_COMPLETE",
            "LogicalResourceId": "WebHostBucket01",
            "PhysicalResourceId": "my-webhosting-bucket01"
        },
        {
            "ResourceType": "AWS::S3::BucketPolicy",
            "LastUpdatedTimestamp": "2019-02-06T20:28:28.755Z",
            "ResourceStatus": "CREATE_COMPLETE",
            "LogicalResourceId": "WebHostBucketBucket01Policy",
            "PhysicalResourceId": "my-WebHostBucketBucket01Policy-101"
        }
    ]
