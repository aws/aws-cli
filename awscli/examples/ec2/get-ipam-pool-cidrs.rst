**To get the CIDRs provisioned to an IPAM pool**

The following ``get-ipam-pool-cidrs`` example gets the CIDRs provisioned to an IPAM pool.

Linux command. ::

    aws ec2 get-ipam-pool-cidrs \
        --ipam-pool-id ipam-pool-0533048da7d823723 \
        --filters 'Name=cidr,Values=10.*'

Windows command. ::

    aws ec2 get-ipam-pool-cidrs ^
        --ipam-pool-id ipam-pool-0533048da7d823723 ^
        --filters Name=cidr,Values=10.*

Output::

    {
        "IpamPoolCidr": {
            "Cidr": "10.0.0.0/24",
            "State": "provisioned"
        }
    }