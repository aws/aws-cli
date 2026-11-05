**To retrieve the tagging configuration of a bucket**

The following ``get-bucket-tagging`` example retrieves the tagging configuration for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-tagging \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "TagSet": [
            {
                "Value": "marketing",
                "Key": "organization"
            }
        ]
    }

For more information, see `Using cost allocation S3 bucket tags <https://docs.aws.amazon.com/AmazonS3/latest/userguide/CostAllocTagging.html>`__ in the *Amazon S3 User Guide*.
