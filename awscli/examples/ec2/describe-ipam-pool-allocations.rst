**Example 1: To describe all your IPAM pool allocations**

The following ``describe-ipam-pool-allocations`` example describes all IPAM pool allocations owned by you.

(Linux)::

    aws ec2 describe-ipam-pool-allocations

(Windows)::

    aws ec2 describe-ipam-pool-allocations

Output::

    {
        "IpamPoolAllocations": [
            {
                "Cidr": "10.0.0.0/24",
                "IpamPoolAllocationId": "ipam-pool-alloc-018ecc28043b54ba38e2cd99943cebfbd",
                "Description": "Engineering team allocation",
                "ResourceType": "custom",
                "ResourceOwner": "123456789012",
                "Tags": []
            },
            {
                "Cidr": "10.0.1.0/24",
                "IpamPoolAllocationId": "ipam-pool-alloc-0e6186d73999e47389266a5d6991e6220",
                "ResourceType": "custom",
                "ResourceOwner": "123456789012",
                "Tags": []
            }
        ]
    }

**Example 2: To describe a specific IPAM pool allocation**

The following ``describe-ipam-pool-allocations`` example describes a specific IPAM pool allocation by its ID.

(Linux)::

    aws ec2 describe-ipam-pool-allocations \
        --ipam-pool-allocation-ids ipam-pool-alloc-018ecc28043b54ba38e2cd99943cebfbd

(Windows)::

    aws ec2 describe-ipam-pool-allocations ^
        --ipam-pool-allocation-ids ipam-pool-alloc-018ecc28043b54ba38e2cd99943cebfbd

Output::

    {
        "IpamPoolAllocations": [
            {
                "Cidr": "10.0.0.0/24",
                "IpamPoolAllocationId": "ipam-pool-alloc-018ecc28043b54ba38e2cd99943cebfbd",
                "Description": "Engineering team allocation",
                "ResourceType": "custom",
                "ResourceOwner": "123456789012",
                "Tags": []
            }
        ]
    }

For more information, see `View allocations for a pool <https://docs.aws.amazon.com/vpc/latest/ipam/view-alloc-ipam.html>`__ in the *Amazon VPC IPAM User Guide*.
