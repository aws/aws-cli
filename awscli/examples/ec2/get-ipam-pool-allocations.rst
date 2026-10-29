**To get the CIDRs allocated from an IPAM pool**

The following ``get-ipam-pool-allocations`` example gets the CIDRs allocated from an IPAM pool.

Linux command. ::

    aws ec2 get-ipam-pool-allocations \
        --ipam-pool-id ipam-pool-0533048da7d823723 \
        --filters Name=ipam-pool-allocation-id,Values=ipam-pool-alloc-0e6186d73999e47389266a5d6991e6220

Windows command. ::

    aws ec2 get-ipam-pool-allocations ^
        --ipam-pool-id ipam-pool-0533048da7d823723 ^
        --filters Name=ipam-pool-allocation-id,Values=ipam-pool-alloc-0e6186d73999e47389266a5d6991e6220

Output::

    {
        "IpamPoolAllocations": [
            {
                "Cidr": "10.0.0.0/16",
                "IpamPoolAllocationId": "ipam-pool-alloc-0e6186d73999e47389266a5d6991e6220",
                "ResourceType": "custom",
                "ResourceOwner": "123456789012"
            }
        ]
    }

For more information, see `View IPAM pool allocations <https://docs.aws.amazon.com/vpc/latest/ipam/view-alloc-ipam.html>`__ in the *Amazon VPC IPAM User Guide*.
