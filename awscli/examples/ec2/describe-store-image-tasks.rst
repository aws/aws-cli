**To view the progress of an AMI store task**

The following ``describe-store-image-tasks`` example describes the specified AMI store task. ::

    aws ec2 describe-store-image-tasks

Output::

    {
        "AmiId": "ami-1234567890abcdef0",
        "Bucket": "myamibucket",
        "ProgressPercentage": 17,
        "S3objectKey": "ami-1234567890abcdef0.bin",
        "StoreTaskState": "InProgress",
        "StoreTaskFailureReason": null,
        "TaskStartTime": "2021-01-01T01:01:01.001Z"
    }

For more information, see `Store and restore an AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ami-store-restore.html>`__ in the *Amazon EC2 User Guide*.