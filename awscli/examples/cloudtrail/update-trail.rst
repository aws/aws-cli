**To update a trail**

The following ``update-trail`` example updates a trail to use an existing bucket for log delivery. ::

    aws cloudtrail update-trail \
        --name Trail1 \
        --s3-bucket-name amzn-s3-demo-bucket

Output::

    {
        "IncludeGlobalServiceEvents": true, 
        "Name": "Trail1", 
        "TrailARN": "arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail1", 
        "LogFileValidationEnabled": false, 
        "IsMultiRegionTrail": true, 
        "S3BucketName": "amzn-s3-demo-bucket"
    }

For more information, see `Using the update-trail command to update a trail <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail-by-using-the-aws-cli-update-trail.html>`__ in the *AWS CloudTrail User Guide*.
