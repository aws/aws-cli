**To abort the specified multipart upload**

The following ``abort-multipart-upload`` example aborts a multipart upload for the key ``multipart/01`` in the bucket ``amzn-s3-demo-bucket``. ::

    aws s3api abort-multipart-upload \
        --bucket amzn-s3-demo-bucket \
        --key multipart/01 \
        --upload-id dfRtDYU0WWCCcH43C3WFbkRONycyCpTJJvxu2i5GYkZljF.Yxwh6XG7WfS2vC4to6HiV6Yjlx.cph0gtNBtJ8P3URCSbB7rjxI5iEwVDmgaXZOGgkk5nVTW16HOQ5l0R

This command produces no output.

The upload ID required by this command is output by ``create-multipart-upload`` and can also be retrieved with ``list-multipart-uploads``.

For more information, see `Aborting a multipart upload <https://docs.aws.amazon.com/AmazonS3/latest/userguide/abort-mpu.html>`__ in the *Amazon S3 User Guide*.
