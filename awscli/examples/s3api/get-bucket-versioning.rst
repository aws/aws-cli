**To retrieve the versioning configuration of a bucket**

The following ``get-bucket-versioning`` example retrieves the versioning configuration for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-versioning \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "Status": "Enabled"
    }

For more information, see `Retaining multiple versions of objects with S3 Versioning <https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html>`__ in the *Amazon S3 User Guide*.
