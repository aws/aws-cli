**To describe your Internet gateways**

This example describes your Internet gateways.

Command::

  aws ec2 describe-internet-gateways

Output::

  {
      "InternetGateways": [
          {
              "Tags": [],
              "InternetGatewayId": "igw-c0a643a9",
              "Attachments": [
                  {
                      "State": "available",
                      "VpcId": "vpc-a01106c2"
                  }
              ]
          },
          {
              "Tags": [],
              "InternetGatewayId": "igw-046d7966",
              "Attachments": []
          }
      ]  
  }
  
**To describe the Internet gateway for a specific VPC**

This example describes the Internet gateway for the specified VPC.

Command::

  aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=vpc-a01106c2"

Output::

  {
      "InternetGateways": [
          {
              "Tags": [],
              "InternetGatewayId": "igw-c0a643a9",
              "Attachments": [
                  {
                      "State": "available",
                      "VpcId": "vpc-a01106c2"
                  }
              ]
          }
      ]  
  }
