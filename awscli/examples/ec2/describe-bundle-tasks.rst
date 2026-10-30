**To describe your bundle tasks**

The following ``describe-bundle-tasks`` example describes all of your bundle tasks. ::

    aws ec2 describe-bundle-tasks

Output::

    {
        "BundleTasks": [
            {
                "UpdateTime": "2015-09-15T13:26:54.000Z",
                "InstanceId": "i-1234567890abcdef0",
                "Storage": {
                    "S3": {
                        "Prefix": "winami",
                        "Bucket": "amzn-s3-demo-bucket"
                    }
                },
                "State": "bundling",
                "StartTime": "2015-09-15T13:24:35.000Z",
                "Progress": "3%",
                "BundleId": "bun-2a4e041c"
            }
        ]
    }

For more information, see `Create an Amazon S3-backed AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/creating-an-ami-instance-store.html>`__ in the *Amazon EC2 User Guide*.
