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

