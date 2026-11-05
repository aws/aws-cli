**To associate an IPv6 CIDR block with a subnet**

The following ``associate-subnet-cidr-block`` example associates an IPv6 CIDR block with the specified subnet. ::

    aws ec2 associate-subnet-cidr-block \
        --subnet-id subnet-5f46ec3b \
        --ipv6-cidr-block 2001:db8:1234:1a00::/64

Output::

    {
        "SubnetId": "subnet-5f46ec3b",
        "Ipv6CidrBlockAssociation": {
            "Ipv6CidrBlock": "2001:db8:1234:1a00::/64",
            "AssociationId": "subnet-cidr-assoc-3aa54053",
            "Ipv6CidrBlockState": {
                "State": "associating"
            }
        }
    }

For more information, see `Add or remove an IPv6 CIDR block from your subnet <https://docs.aws.amazon.com/vpc/latest/userguide/subnet-associate-ipv6-cidr.html>`__ in the *Amazon VPC User Guide*.
