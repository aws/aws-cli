**To wait until a VPC peering connection exists**

The following ``wait vpc-peering-connection-exists`` example pauses and continues only when it can confirm that the specified VPC peering connection exists. ::

    aws ec2 wait vpc-peering-connection-exists \
        --vpc-peering-connection-ids pcx-1234567890abcdef0

This command produces no output.

For more information, see `Create a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/create-vpc-peering-connection.html>`__ in the *Amazon VPC Peering Guide*.
