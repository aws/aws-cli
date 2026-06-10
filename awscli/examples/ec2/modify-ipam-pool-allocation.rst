**To modify an IPAM pool allocation**

The following ``modify-ipam-pool-allocation`` example modifies the description of an IPAM pool allocation.

(Linux)::

    aws ec2 modify-ipam-pool-allocation \
        --ipam-pool-allocation-id ipam-pool-alloc-018ecc28043b54ba38e2cd99943cebfbd \
        --description "Engineering team  us-west-2 allocation"

(Windows)::

    aws ec2 modify-ipam-pool-allocation ^
        --ipam-pool-allocation-id ipam-pool-alloc-018ecc28043b54ba38e2cd99943cebfbd ^
        --description "Engineering team  us-west-2 allocation"

Output::

    {
        "IpamPoolAllocation": {
            "Cidr": "10.0.0.0/24",
            "IpamPoolAllocationId": "ipam-pool-alloc-018ecc28043b54ba38e2cd99943cebfbd",
            "Description": "Engineering team  us-west-2 allocation",
            "ResourceType": "custom",
            "ResourceOwner": "123456789012"
        }
    }

For more information, see `Modify an IPAM pool allocation <https://docs.aws.amazon.com/vpc/latest/ipam/modify-alloc-ipam.html>`__ in the *Amazon VPC IPAM User Guide*.
