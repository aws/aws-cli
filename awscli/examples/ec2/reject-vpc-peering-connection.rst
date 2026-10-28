**To reject a VPC peering connection**

The following ``reject-vpc-peering-connection`` example rejects the specified VPC peering connection request. ::

    aws ec2 reject-vpc-peering-connection --vpc-peering-connection-id pcx-1a2b3c4d

Output::

    {
        "Return": true
    }