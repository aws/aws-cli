**To retrieve the server-side encryption configuration for a bucket**

The following ``get-bucket-encryption`` example retrieves the server-side encryption configuration for the bucket ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-encryption \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "ServerSideEncryptionConfiguration": {
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        }
    }

For more information, see `Setting default server-side encryption behavior for Amazon S3 buckets <https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-encryption.html>`__ in the *Amazon S3 User Guide*.
