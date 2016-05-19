**To describe your Elastic IP addresses**

This example describes your Elastic IP addresses.

Command::

  aws ec2 describe-addresses

Output::

  {
      "Addresses": [
          {
              "InstanceId": null,
              "PublicIp": "198.51.100.0",
              "Domain": "standard"
          },
          {
              "PublicIp": "203.0.113.0",
              "Domain": "vpc",
              "AllocationId": "eipalloc-64d5890a"
          }
      ]
  }

**To describe your Elastic IP addresses for EC2-VPC**

This example describes your Elastic IP addresses for use with instances in a VPC.

Command::

  aws ec2 describe-addresses --filters "Name=domain,Values=vpc"

Output::

  {
      "Addresses": [
          {
              "PublicIp": "203.0.113.0",
              "Domain": "vpc",
              "AllocationId": "eipalloc-64d5890a"
          }
      ]
  }

This example describes the Elastic IP address with the allocation ID ``eipalloc-282d9641``, which is associated with an instance in EC2-VPC.

Command::

    aws ec2 describe-addresses --allocation-ids eipalloc-282d9641

Output::

    {
        "Addresses": [
            {
                "Domain": "vpc",
                "InstanceId": "i-1234567890abcdef0",
                "NetworkInterfaceId": "eni-1a2b3c4d",
                "AssociationId": "eipassoc-123abc12",
                "NetworkInterfaceOwnerId": "1234567891012",
                "PublicIp": "203.0.113.25",
                "AllocationId": "eipalloc-282d9641",
                "PrivateIpAddress": "10.251.50.12"
            }
        ]
    }

This example describes the Elastic IP address associated with a particular private IP address in EC2-VPC.

Command::

    aws ec2 describe-addresses --filters "Name=private-ip-address,Values=10.251.50.12"

**To describe your Elastic IP addresses in EC2-Classic**

This example describes your Elastic IP addresses for use in EC2-Classic.

Command::

    aws ec2 describe-addresses --filters "Name=domain,Values=standard"
    
Output::

    {
        "Addresses": [
            {
                "InstanceId": null, 
                "PublicIp": "203.0.110.25", 
                "Domain": "standard"
            }
        ]
    }

This example describes the Elastic IP address with the value ``203.0.110.25``, which is associated with an instance in EC2-Classic.

Command::

    aws ec2 describe-addresses --public-ips 203.0.110.25

Output::

    {
        "Addresses": [
            {
                "InstanceId": "i-0598c7d356eba48d7", 
                "PublicIp": "203.0.110.25", 
                "Domain": "standard"
            }
        ]
    }

