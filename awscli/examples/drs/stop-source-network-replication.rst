**To stop source network replication**

The following ``stop-source-network-replication`` example stops replication for the specified source network. ::

    aws drs stop-source-network-replication \
        --source-network-id sn-1234567890abcdef0

Output::

    {
        "sourceNetwork": {
            "arn": "arn:aws:drs:us-west-2:123456789012:source-network/sn-1234567890abcdef0",
            "replicationStatus": "STOPPED",
            "sourceNetworkID": "sn-1234567890abcdef0",
            "sourceVpcID": "vpc-1234567890abcdef0",
            "tags": {}
        }
    }

For more information, see `Source network recovery <https://docs.aws.amazon.com/drs/latest/userguide/source-network-recovery.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
