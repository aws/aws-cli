**To wait until a VPC peering connection is deleted**

The following ``wait vpc-peering-connection-deleted`` example pauses and resumes running only after it confirms that the specified VPC peering connection is deleted. ::

    aws ec2 wait vpc-peering-connection-deleted \
        --vpc-peering-connection-ids pcx-1234567890abcdef0

This command produces no output.

For more information, see `Delete a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/delete-vpc-peering-connection.html>`__ in the *Amazon VPC Peering Guide*.
