**To delete a VPC peering connection**

The following ``delete-vpc-peering-connection`` example deletes the specified VPC peering connection. ::

    aws ec2 delete-vpc-peering-connection \
        --vpc-peering-connection-id pcx-1a2b3c4d

Output::

    {
        "Return": true
    }

For more information, see `Delete a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/delete-vpc-peering-connection.html>`__ in the *Amazon VPC Peering Guide*.
