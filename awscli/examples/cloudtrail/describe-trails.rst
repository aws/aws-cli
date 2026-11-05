**To describe a trail**

The following ``describe-trails`` example returns the settings for ``Trail1`` and ``Trail2``. ::

    aws cloudtrail describe-trails \
        --trail-name-list Trail1 Trail2

Output::

    {
        "trailList": [
            {
                "IncludeGlobalServiceEvents": true, 
                "Name": "Trail1", 
                "TrailARN": "arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail1", 
                "LogFileValidationEnabled": false, 
                "IsMultiRegionTrail": false, 
                "S3BucketName": "amzn-s3-demo-bucket", 
                "CloudWatchLogsRoleArn": "arn:aws:iam::123456789012:role/CloudTrail_CloudWatchLogs_Role", 
                "CloudWatchLogsLogGroupArn": "arn:aws:logs:us-west-2:123456789012:log-group:CloudTrail:*", 
                "SnsTopicName": "my-topic", 
                "HomeRegion": "us-west-2"
            }, 
            {
                "IncludeGlobalServiceEvents": true, 
                "Name": "Trail2", 
                "S3KeyPrefix": "my-prefix", 
                "TrailARN": "arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail2", 
                "LogFileValidationEnabled": false, 
                "IsMultiRegionTrail": false, 
                "S3BucketName": "amzn-s3-demo-bucket2", 
                "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "HomeRegion": "us-west-2"
            }
        ]
    }

For more information, see `Managing trails with the AWS CLI <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-additional-cli-commands.html>`__ in the *AWS CloudTrail User Guide*.
