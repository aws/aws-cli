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
                        "Bucket": "bundletasks"
                    }
                },
                "State": "bundling",
                "StartTime": "2015-09-15T13:24:35.000Z",
                "Progress": "3%",
                "BundleId": "bun-2a4e041c"
            }
        ]
    }