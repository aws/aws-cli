**To edit block public access settings for an account**

The following ``put-public-access-block`` example toggles all block public access settings to ``true`` for the specified account. ::

    aws s3control put-public-access-block \
        --account-id 123456789012 \
        --public-access-block-configuration '{"BlockPublicAcls": true, "IgnorePublicAcls": true, "BlockPublicPolicy": true, "RestrictPublicBuckets": true}'

This command produces no output.

For more information, see `Configuring block public access settings for your account <https://docs.aws.amazon.com/AmazonS3/latest/userguide/configuring-block-public-access-account.html>`__ in the *Amazon S3 User Guide*.
