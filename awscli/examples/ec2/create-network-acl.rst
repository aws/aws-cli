**To create a network ACL**

The following ``create-network-acl`` example creates a network ACL for the specified VPC. ::

    aws ec2 create-network-acl \
        --vpc-id vpc-a01106c2

Output::

    {
        "NetworkAcl": {
            "Associations": [],
            "NetworkAclId": "acl-5fb85d36",
            "VpcId": "vpc-a01106c2",
            "Tags": [],
            "Entries": [
                {
                    "CidrBlock": "0.0.0.0/0",
                    "RuleNumber": 32767,
                    "Protocol": "-1",
                    "Egress": true,
                    "RuleAction": "deny"
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "RuleNumber": 32767,
                    "Protocol": "-1",
                    "Egress": false,
                    "RuleAction": "deny"
                }
            ],
            "IsDefault": false
        }
    }

For more information, see `Create a network ACL for your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/create-network-acl.html>`__ in the *Amazon VPC User Guide*.
