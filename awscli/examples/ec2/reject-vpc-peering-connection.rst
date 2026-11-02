**To reject a VPC peering connection**

The following ``reject-vpc-peering-connection`` example rejects the specified VPC peering connection request. ::

    aws ec2 reject-vpc-peering-connection \
        --vpc-peering-connection-id pcx-1a2b3c4d

Output::

    {
        "Return": true
    }

For more information, see `Accept or reject a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/accept-vpc-peering-connection.html>`__ in the *Amazon VPC Peering Guide*.
