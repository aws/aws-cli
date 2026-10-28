**To enable versioning on a bucket**

The following ``put-bucket-versioning`` example enables versioning on a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api put-bucket-versioning \
        --bucket amzn-s3-demo-bucket \
        --versioning-configuration Status=Enabled

The following command enables versioning and uses an MFA code. ::

    aws s3api put-bucket-versioning \
        --bucket amzn-s3-demo-bucket \
        --versioning-configuration Status=Enabled \
        --mfa "SERIAL 123456"
