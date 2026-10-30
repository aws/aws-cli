**To retrieve the versioning configuration of a bucket**

The following ``get-bucket-versioning`` example retrieves the versioning configuration for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-versioning --bucket amzn-s3-demo-bucket

Output::

    {
        "Status": "Enabled"
    }
