**To view security groups that can be associated with network interfaces in a specified VPC.**

The following ``get-security-groups-for-vpc`` example shows the security groups that can be associated with network interfaces in the VPC. ::

    aws ec2 get-security-groups-for-vpc \
        --vpc-id vpc-6c31a611

Output::

    {
        "SecurityGroupForVpcs": [
            {
                "Description": "launch-wizard-36 created 2022-08-29T15:59:35.338Z",
                "GroupName": "launch-wizard-36",
                "OwnerId": "123456789012",
                "GroupId": "sg-007e0c3027ee885f5",
                "Tags": [],
                "PrimaryVpcId": "vpc-6c31a611"
            },
            {
                "Description": "launch-wizard-18 created 2024-01-19T20:22:27.527Z",
                "GroupName": "launch-wizard-18",
                "OwnerId": "123456789012",
                "GroupId": "sg-0147193bef51c9eef",
                "Tags": [],
                "PrimaryVpcId": "vpc-6c31a611"
            }
        ]
    }

For more information, see `Associate security groups with multiple VPCs <https://docs.aws.amazon.com/vpc/latest/userguide/security-group-assoc.html>`__ in the *Amazon VPC User Guide*.
