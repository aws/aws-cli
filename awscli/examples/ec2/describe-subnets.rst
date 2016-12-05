**To describe your subnets**

This example describes your subnets.

Command::

  aws ec2 describe-subnets 

Output::

  {
      "Subnets": [
          {
              "VpcId": "vpc-a01106c2",
              "AvailableIpAddressCount": 251,
              "MapPublicIpOnLaunch": false,
              "DefaultForAz": false,
              "Ipv6CidrBlockAssociationSet": [],
              "State": "available",
              "AvailabilityZone": "us-east-1c",
              "SubnetId": "subnet-9d4a7b6c",
              "CidrBlock": "10.0.1.0/24",
              "AssignIpv6AddressOnCreation": false
          },
          {
            "VpcId": "vpc-31896b55", 
            "AvailableIpAddressCount": 251, 
            "MapPublicIpOnLaunch": false, 
            "DefaultForAz": false, 
            "Ipv6CidrBlockAssociationSet": [
                {
                    "Ipv6CidrBlock": "2001:db8:1234:a101::/64", 
                    "AssociationId": "subnet-cidr-assoc-30e7e348", 
                    "Ipv6CidrBlockState": {
                        "State": "ASSOCIATED"
                    }
                }
            ], 
            "State": "available", 
            "AvailabilityZone": "us-east-1a", 
            "SubnetId": "subnet-4204d234", 
            "CidrBlock": "10.0.1.0/24", 
            "AssignIpv6AddressOnCreation": false
        }
      ]  
  }
  
**To describe the subnets for a specific VPC**

This example describes the subnets for the specified VPC.

Command::

  aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-a01106c2"

**To describe subnets with a specific tag**

This example lists subnets with the tag ``Name=MySubnet`` and returns the output in text format.

Command::

  aws ec2 describe-subnets --filters Name=tag:Name,Values=MySubnet --output text

Output::

  SUBNETS	False	us-east-1a	251	10.0.1.0/24	False	False	available	subnet-5f46ec3b	vpc-a034d6c4
  TAGS	Name	MySubnet