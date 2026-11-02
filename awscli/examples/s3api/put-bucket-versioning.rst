**To enable versioning on a bucket**

The following ``put-bucket-versioning`` example enables versioning on a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api put-bucket-versioning \
        --bucket amzn-s3-demo-bucket \
        --versioning-configuration Status=Enabled

This command produces no output.

The following command enables versioning and uses an MFA code. ::

    aws s3api put-bucket-versioning \
        --bucket amzn-s3-demo-bucket \
        --versioning-configuration Status=Enabled \
        --mfa "SERIAL 123456"

This command produces no output.

For more information, see `Retaining multiple versions of objects with S3 Versioning <https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html>`__ in the *Amazon S3 User Guide*.
