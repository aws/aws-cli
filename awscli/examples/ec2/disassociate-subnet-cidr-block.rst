**To disassociate an IPv6 CIDR block from a subnet**

The following ``disassociate-subnet-cidr-block`` example disassociates an IPv6 CIDR block from a subnet using the association ID for the CIDR block. ::

    aws ec2 disassociate-subnet-cidr-block \
        --association-id subnet-cidr-assoc-3aa54053

Output::

    {
        "SubnetId": "subnet-5f46ec3b",
        "Ipv6CidrBlockAssociation": {
            "Ipv6CidrBlock": "2001:db8:1234:1a00::/64",
            "AssociationId": "subnet-cidr-assoc-3aa54053",
            "Ipv6CidrBlockState": {
                "State": "disassociating"
            }
        }
    }

For more information, see `Add or remove an IPv6 CIDR block from your subnet <https://docs.aws.amazon.com/vpc/latest/userguide/subnet-associate-ipv6-cidr.html>`__ in the *Amazon VPC User Guide*.
