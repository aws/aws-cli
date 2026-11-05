**To create a trail**

The following ``create-trail`` example creates a multi-region trail named ``Trail1`` and specifies an S3 bucket. ::

    aws cloudtrail create-trail \
        --name Trail1 \
        --s3-bucket-name amzn-s3-demo-bucket \
        --is-multi-region-trail

Output::

    {
        "IncludeGlobalServiceEvents": true, 
        "Name": "Trail1", 
        "TrailARN": "arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail1", 
        "LogFileValidationEnabled": false, 
        "IsMultiRegionTrail": true, 
        "S3BucketName": "amzn-s3-demo-bucket"
    }

For more information, see `Using the create-trail command to create a trail <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail-by-using-the-aws-cli-create-trail.html>`__ in the *AWS CloudTrail User Guide*.
