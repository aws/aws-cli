**Example 1: To release an Elastic IP address for EC2-Classic**

The following ``release-address`` example releases an Elastic IP address for use with instances in EC2-Classic. This command produces no output. ::

    aws ec2 release-address \
        --public-ip 198.51.100.0

**Example 2: To release an Elastic IP address for EC2-VPC**

The following ``release-address`` example releases an Elastic IP address for use with instances in a VPC. This command produces no output. ::

    aws ec2 release-address \
        --allocation-id eipalloc-64d5890a
