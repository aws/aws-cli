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
        --domain vpc

Output::

    {
        "PublicIp": "203.0.113.0",
        "PublicIpv4Pool": "amazon",
        "Domain": "vpc",
        "AllocationId": "eipalloc-07b6d55388acd1884"
    }
