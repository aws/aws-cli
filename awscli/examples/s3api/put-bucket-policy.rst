**To apply a policy to a bucket**

The following ``put-bucket-policy`` example allows all users to retrieve any object in *amzn-s3-demo-bucket* except those in the *MySecretFolder*. It also
grants ``put`` and ``delete`` permission to the root user of the AWS account ``1234-5678-9012``. ::

    aws s3api put-bucket-policy \
        --bucket amzn-s3-demo-bucket \
        --policy file://policy.json

Contents of ``policy.json``::

    {
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::amzn-s3-demo-bucket/*"
            },
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::amzn-s3-demo-bucket/MySecretFolder/*"
            },
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789012:root"
                },
                "Action": [
                    "s3:DeleteObject",
                    "s3:PutObject"
                ],
                "Resource": "arn:aws:s3:::amzn-s3-demo-bucket/*"
            }
        ]
    }

This command produces no output.

For more information, see `Bucket policies for Amazon S3 <https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html>`__ in the *Amazon S3 User Guide*.
