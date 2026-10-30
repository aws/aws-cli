**To list the names of all your Amazon S3 buckets**

The following ``list-buckets`` example displays the names of all your Amazon S3 buckets (across all
regions). ::

    aws s3api list-buckets \
        --query "Buckets[].Name"

Output::

    [
        "amzn-s3-demo-bucket1",
        "amzn-s3-demo-bucket2"
    ]

The query option filters the output of ``list-buckets`` down to only the bucket names.

For more information, see `General purpose buckets overview <https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingBucket.html>`__ in the *Amazon S3 User Guide*.
