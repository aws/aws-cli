**To create a multipart upload**

The following ``create-multipart-upload`` example creates a multipart upload in the bucket ``amzn-s3-demo-bucket`` with the key ``multipart/01``. ::

    aws s3api create-multipart-upload \
        --bucket amzn-s3-demo-bucket \
        --key 'multipart/01'

Output::

    {
        "Bucket": "amzn-s3-demo-bucket",
        "UploadId": "dfRtDYU0WWCCcH43C3WFbkRONycyCpTJJvxu2i5GYkZljF.Yxwh6XG7WfS2vC4to6HiV6Yjlx.cph0gtNBtJ8P3URCSbB7rjxI5iEwVDmgaXZOGgkk5nVTW16HOQ5l0R",
        "Key": "multipart/01"
    }

The completed file will be named ``01`` in a folder called ``multipart`` in the bucket ``amzn-s3-demo-bucket``. Save the upload ID, key and bucket name for use with the ``upload-part`` command.

For more information, see `Uploading and copying objects using multipart upload in Amazon S3 <https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html>`__ in the *Amazon S3 User Guide*.
