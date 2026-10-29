**To edit a container policy**

The following ``put-container-policy`` example assigns a different policy to the specified container. In this example, the updated policy is defined in a file named ``LiveEventsContainerPolicy.json``. ::

    aws mediastore put-container-policy \
        --container-name LiveEvents \
        --policy file://LiveEventsContainerPolicy.json

Contents of ``LiveEventsContainerPolicy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "MediaStoreFullAccess",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789012:root"
                },
                "Action": "mediastore:*",
                "Resource": "arn:aws:mediastore:us-west-2:123456789012:container/LiveEvents/*",
                "Condition": {
                    "Bool": {
                        "aws:SecureTransport": "true"
                    }
                }
            }
        ]
    }

This command produces no output.
