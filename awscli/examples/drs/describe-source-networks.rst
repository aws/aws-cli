**To describe source networks**

The following ``describe-source-networks`` example describes all source networks in your account. ::

    aws drs describe-source-networks \
        --filters '{}'

Output::

    {
        "items": [
            {
                "arn": "arn:aws:drs:us-west-2:123456789012:source-network/sn-1234567890abcdef0",
                "cfnStackName": "StackName",
                "lastUpdatedDateTime": "2024-06-15T18:00:00.000Z",
                "replicationStatus": "STOPPED",
                "sourceNetworkID": "sn-1234567890abcdef0",
                "sourceRegion": "us-west-2",
                "sourceVpcID": "vpc-1234567890abcdef0",
                "tags": {}
            }
        ]
    }

For more information, see `Source network recovery <https://docs.aws.amazon.com/drs/latest/userguide/source-network-recovery.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
