**To create a source network**

The following ``create-source-network`` example creates a source network for the specified VPC. ::

    aws drs create-source-network \
        --origin-account-id 123456789012 \
        --origin-region us-west-2 \
        --vpc-id vpc-1234567890abcdef0

Output::

    {
        "sourceNetworkID": "sn-1234567890abcdef0"
    }

For more information, see `Source network recovery <https://docs.aws.amazon.com/drs/latest/userguide/source-network-recovery.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
