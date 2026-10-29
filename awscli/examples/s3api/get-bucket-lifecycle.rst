**To retrieve the lifecycle configuration of a bucket**

The following ``get-bucket-lifecycle`` example retrieves the lifecycle configuration for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-lifecycle \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "Rules": [
            {
                "ID": "Move to Glacier after sixty days (objects in logs/2015/)",
                "Prefix": "logs/2015/",
                "Status": "Enabled",
                "Transition": {
                    "Days": 60,
                    "StorageClass": "GLACIER"
                }
            },
            {
                "Expiration": {
                    "Date": "2016-01-01T00:00:00.000Z"
                },
                "ID": "Delete 2014 logs in 2016.",
                "Prefix": "logs/2014/",
                "Status": "Enabled"
            }
        ]
    }

For more information, see `Managing the lifecycle of objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html>`__ in the *Amazon S3 User Guide*.
