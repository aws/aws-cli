**Example 1: To release an Elastic IP address for EC2-Classic**

The following ``release-address`` example releases an Elastic IP address for use with instances in EC2-Classic. ::

    aws ec2 release-address \
        --public-ip 198.51.100.0

This command produces no output.

**Example 2: To release an Elastic IP address for EC2-VPC**

The following ``release-address`` example releases an Elastic IP address for use with instances in a VPC. ::

    aws ec2 release-address \
        --allocation-id eipalloc-64d5890a

This command produces no output.
