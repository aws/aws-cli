**To create and configure AWS resources for a trail**

The following ``create-subscription`` command creates a new S3 bucket and SNS topic for ``Trail1``. ::

    aws cloudtrail create-subscription \
        --name Trail1 \
        --s3-new-bucket amzn-s3-demo-bucket \
        --sns-new-topic my-topic

Output::

    Setting up new S3 bucket amzn-s3-demo-bucket...
    Setting up new SNS topic my-topic...
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
                    "SnsTopicName": "my-topic", 
                    "HomeRegion": "us-east-1"
                }
            ], 
            "ResponseMetadata": {
            "HTTPStatusCode": 200, 
            "RequestId": "f39e51f6-c615-11e5-85bd-d35ca21ee3e2"
            }
        }
    Starting CloudTrail service...
    Logs will be delivered to my-bucket