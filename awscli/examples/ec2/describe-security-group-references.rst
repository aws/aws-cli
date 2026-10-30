**To describe security group references**

The following ``describe-security-group-references`` example describes the security group references for ``sg-bbbbb22222``. The response indicates that security group ``sg-bbbbb22222`` is being referenced by a security group in VPC ``vpc-aaaaaaaa``. ::

    aws ec2 describe-security-group-references \
        --group-id sg-bbbbb22222

Output::

    {
        "SecurityGroupsReferenceSet": [
            {
                "ReferencingVpcId": "vpc-aaaaaaaa ",
                "GroupId": "sg-bbbbb22222",
                "VpcPeeringConnectionId": "pcx-b04deed9"
            }
        ]
    }