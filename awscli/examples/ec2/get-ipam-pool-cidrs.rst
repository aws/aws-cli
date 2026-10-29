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
        "IpamPoolCidrs": [
            {
                "Cidr": "10.0.0.0/24",
                "State": "provisioned"
            }
        ]
    }

For more information, see `Provision CIDRs to a pool <https://docs.aws.amazon.com/vpc/latest/ipam/prov-cidr-ipam.html>`__ in the *Amazon VPC IPAM User Guide*.
