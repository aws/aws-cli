**To describe security group references**

The following ``describe-security-group-references`` example describes the security group references for ``sg-bbbbb22222``. The response indicates that security group ``sg-bbbbb22222`` is being referenced by a security group in VPC ``vpc-aaaaaaaa``. ::

    aws ec2 describe-security-group-references \
        --group-id sg-bbbbb22222

Output::

    {
        "SecurityGroupReferenceSet": [
            {
                "ReferencingVpcId": "vpc-aaaaaaaa ",
                "GroupId": "sg-bbbbb22222",
                "VpcPeeringConnectionId": "pcx-b04deed9"
            }
        ]
    }

For more information, see `Identify your referenced security groups <https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-security-groups.html#vpc-peering-referenced-groups>`__ in the *Amazon VPC Peering Guide*.
