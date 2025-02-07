**To update the configuration settings for a trail**

The following ``update-subscription`` example updates the trail to specify a new S3 bucket and SNS topic. ::

    aws cloudtrail update-subscription \
        --name Trail1 \
        --s3-new-bucket amzn-s3-demo-bucket \
        --sns-new-topic my-topic-new

Output::

    Setting up new S3 bucket amzn-s3-demo-bucket...
    Setting up new SNS topic my-topic-new...
    Creating/updating CloudTrail configuration...
    CloudTrail configuration:
    {
        "trailList": [
            {
                "IncludeGlobalServiceEvents": true, 
                "Name": "Trail1", 
                "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/Trail1", 
                "LogFileValidationEnabled": false, 
                "IsMultiRegionTrail": false, 
                "S3BucketName": "amzn-s3-demo-bucket", 
                "SnsTopicName": "my-topic-new", 
                "HomeRegion": "us-east-1"
            }
        ], 
        "ResponseMetadata": {
            "HTTPStatusCode": 200, 
            "RequestId": "31126f8a-c616-11e5-9cc6-2fd637936879"
        }
    }
