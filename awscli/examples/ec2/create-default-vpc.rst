**To create a default VPC**

The following ``create-default-vpc`` example creates a default VPC. ::

    aws ec2 create-default-vpc

Output::

    {
        "Vpc": {
            "VpcId": "vpc-8eaae5ea",
            "InstanceTenancy": "default",
            "Tags": [],
            "Ipv6CidrBlockAssociationSet": [],
            "State": "pending",
            "DhcpOptionsId": "dopt-af0c32c6",
            "CidrBlock": "172.31.0.0/16",
            "IsDefault": true
        }
    }