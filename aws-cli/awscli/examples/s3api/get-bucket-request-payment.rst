**To retrieve the request payment configuration for a bucket**

The following ``get-bucket-request-payment`` example retrieves the requester pays configuration for the specified bucket. ::

    aws s3api get-bucket-request-payment \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "Payer": "BucketOwner"
    }

For more information, see `Using Requester Pays general purpose buckets for storage transfers and usage <https://docs.aws.amazon.com/AmazonS3/latest/userguide/RequesterPaysBuckets.html>`__ in the *Amazon S3 User Guide*.
