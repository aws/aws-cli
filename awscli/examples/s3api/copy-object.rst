**To copy an object**

The following ``copy-object`` example copies an object from ``bucket-1`` to ``amzn-s3-demo-bucket2``. ::

    aws s3api copy-object \
        --copy-source bucket-1/test.txt \
        --key test.txt \
        --bucket amzn-s3-demo-bucket2

Output::

    {
        "CopyObjectResult": {
            "LastModified": "2015-11-10T01:07:25.000Z",
            "ETag": "\"589c8b79c230a6ecd5a7e1d040a9a030\""
        },
        "VersionId": "YdnYvTCVDqRRFA.NFJjy36p0hxifMlkA"
    }

For more information, see `Copying, moving, and renaming objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/copy-object.html>`__ in the *Amazon S3 User Guide*.
