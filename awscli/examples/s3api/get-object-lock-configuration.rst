**To retrieve an object lock configuration for a bucket**

The following ``get-object-lock-configuration`` example retrieves the object lock configuration for the specified bucket. ::

    aws s3api get-object-lock-configuration \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "ObjectLockConfiguration": {
            "ObjectLockEnabled": "Enabled",
            "Rule": {
                "DefaultRetention": {
                    "Mode": "COMPLIANCE", 
                    "Days": 50
                }
            }
        }
    }

For more information, see `Configuring S3 Object Lock <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-configure.html>`__ in the *Amazon S3 User Guide*.
