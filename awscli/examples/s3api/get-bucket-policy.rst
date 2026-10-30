**Example 1: To retrieve a bucket policy**

The following ``get-bucket-policy`` example retrieves the bucket policy for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-policy \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "Policy": "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Sid\":\"\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::amzn-s3-demo-bucket/*\"},{\"Sid\":\"\",\"Effect\":\"Deny\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::amzn-s3-demo-bucket/secret/*\"}]}"
    }

**Example 2: To get and put a bucket policy**

The following ``get-bucket-policy`` example shows how you can download an Amazon S3 bucket policy,
make modifications to the file, and then use ``put-bucket-policy`` to
apply the modified bucket policy.  To download the bucket policy to a file,
run the following command. ::

    aws s3api get-bucket-policy \
        --bucket amzn-s3-demo-bucket \
        --query Policy \
        --output text > policy.json

This command produces no output.

You can then modify the ``policy.json`` file as needed.  Finally you can apply
this modified policy back to the S3 bucket by running the following command. ::

    aws s3api put-bucket-policy \
        --bucket amzn-s3-demo-bucket \
        --policy file://policy.json

Contents of ``policy.json``::

    {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::amzn-s3-demo-bucket/*"
            },
            {
                "Sid": "",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::amzn-s3-demo-bucket/secret/*"
            }
        ]
    }

This command produces no output.

For more information, see `Bucket policies for Amazon S3 <https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html>`__ in the *Amazon S3 User Guide*.
