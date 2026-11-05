**To cancel a bundle task**

The following ``cancel-bundle-task`` example cancels bundle task ``bun-2a4e041c``. ::

    aws ec2 cancel-bundle-task \
        --bundle-id bun-2a4e041c

Output::

    {
        "BundleTask": {
            "UpdateTime": "2015-09-15T13:27:40.000Z",
            "InstanceId": "i-1234567890abcdef0",
            "Storage": {
                "S3": {
                    "Prefix": "winami",
                    "Bucket": "amzn-s3-demo-bucket"
                }
            },
            "State": "cancelling",
            "StartTime": "2015-09-15T13:24:35.000Z",
            "BundleId": "bun-2a4e041c"
        }
    }

For more information, see `AMI types and characteristics in Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ComponentsAMIs.html>`__ in the *Amazon EC2 User Guide*.
