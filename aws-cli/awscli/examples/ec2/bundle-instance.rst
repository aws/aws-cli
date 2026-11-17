**To bundle an instance**

The following ``bundle-instance`` example bundles instance ``i-1234567890abcdef0`` to a bucket called ``amzn-s3-demo-bucket``. Before you specify values for your access key IDs, review and follow the guidance in `Manage access keys for IAM users <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html>`__ in the *IAM User Guide*. ::

    aws ec2 bundle-instance \
        --instance-id i-1234567890abcdef0 \
        --bucket amzn-s3-demo-bucket \
        --prefix winami \
        --owner-akid AK12AJEXAMPLE \
        --owner-sak example123example

Output::

    {
        "BundleTask": {
            "UpdateTime": "2015-09-15T13:30:35.000Z",
            "InstanceId": "i-1234567890abcdef0",
            "Storage": {
                "S3": {
                    "Prefix": "winami",
                    "Bucket": "amzn-s3-demo-bucket"
                }
            },
            "State": "pending",
            "StartTime": "2015-09-15T13:30:35.000Z",
            "BundleId": "bun-294e041f"
        }
    }

For more information, see `AMI types and characteristics in Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ComponentsAMIs.html>`__ in the *Amazon EC2 User Guide*.
