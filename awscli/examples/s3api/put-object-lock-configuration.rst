**To set an object lock configuration on a bucket**

The following ``put-object-lock-configuration`` example sets a 50-day object lock on the specified bucket. ::

    aws s3api put-object-lock-configuration \
        --bucket amzn-s3-demo-bucket \
        --object-lock-configuration '{ "ObjectLockEnabled": "Enabled", "Rule": { "DefaultRetention": { "Mode": "COMPLIANCE", "Days": 50 }}}'

This command produces no output.

For more information, see `Locking objects with Object Lock <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html>`__ in the *Amazon S3 User Guide*.
