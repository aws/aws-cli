**To retrieve the lifecycle configuration of a bucket**

The following ``get-bucket-lifecycle-configuration`` example retrieves the lifecycle configuration for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-lifecycle-configuration \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "Rules": [
            {
                "ID": "Move rotated logs to Glacier",
                "Prefix": "rotated/",
                "Status": "Enabled",
                "Transitions": [
                    {
                        "Date": "2015-11-10T00:00:00.000Z",
                        "StorageClass": "GLACIER"
                    }
                ]
            },
            {
                "Status": "Enabled",
                "Prefix": "",
                "NoncurrentVersionTransitions": [
                    {
                        "NoncurrentDays": 0,
                        "StorageClass": "GLACIER"
                    }
                ],
                "ID": "Move old versions to Glacier"
            }
        ]
    }

For more information, see `Managing the lifecycle of objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html>`__ in the *Amazon S3 User Guide*.
