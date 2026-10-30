**To list the names of all your Amazon S3 buckets**

The following ``list-buckets`` example displays the names of all your Amazon S3 buckets (across all
regions). ::

    aws s3api list-buckets \
        --query "Buckets[].Name"

The query option filters the output of ``list-buckets`` down to only the bucket names.

For more information about buckets, see `Working with Amazon S3 Buckets`_ in the *Amazon S3 Developer Guide*.

.. _`Working with Amazon S3 Buckets`: http://docs.aws.amazon.com/AmazonS3/latest/dev/UsingBucket.html
