**Example 1: To allocate an Elastic IP address for EC2-Classic**

The following ``allocate-address`` example allocates an Elastic IP address to use with an instance in EC2-Classic. ::

    aws ec2 allocate-address

Output::

    {
        "PublicIp": "198.51.100.0",
        "PublicIpv4Pool": "amazon",
        "Domain": "standard"
    }

**Example 2: To allocate an Elastic IP address for EC2-VPC**

The following ``allocate-address`` example allocates an Elastic IP address to use with an instance in a VPC. ::

    aws ec2 allocate-address \
        --domain vpc \
        --network-border-group us-west-2-lax-1

Output::

    {
        "PublicIp": "70.224.234.241",
        "AllocationId": "eipalloc-02463d08ceEXAMPLE",
        "PublicIpv4Pool": "amazon",
        "NetworkBorderGroup": "us-west-2-lax-1",
        "Domain": "vpc"
    }
