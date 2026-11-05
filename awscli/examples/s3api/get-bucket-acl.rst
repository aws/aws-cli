**To retrieve the access control list of a bucket**

The following ``get-bucket-acl`` example retrieves the access control list for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-acl \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "Owner": {
            "DisplayName": "my-username",
            "ID": "7009a8971cd538e11f6b6606438875e7c86c5b672f46db45460ddcd087d36c32"
        },
        "Grants": [
            {
                "Grantee": {
                    "DisplayName": "my-username",
                    "ID": "7009a8971cd538e11f6b6606438875e7c86c5b672f46db45460ddcd087d36c32"
                },
                "Permission": "FULL_CONTROL"
            }
        ]
    }

For more information, see `Access control list (ACL) overview <https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html>`__ in the *Amazon S3 User Guide*.
