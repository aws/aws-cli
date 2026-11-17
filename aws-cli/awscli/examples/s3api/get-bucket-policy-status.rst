**To retrieve the policy status for a bucket indicating whether the bucket is public**

The following ``get-bucket-policy-status`` example retrieves the policy status for the bucket ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-policy-status \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "PolicyStatus": {
            "IsPublic": false
        }
    }

For more information, see `Blocking public access to your Amazon S3 storage <https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html>`__ in the *Amazon S3 User Guide*.
