**To create a virtual private gateway**

This example creates a virtual private gateway.

Command::

  aws ec2 create-vpn-gateway --type ipsec.1

Output::

  {
      "VpnGateway": {
          "State": "available",
          "Type": "ipsec.1",
          "VpnGatewayId": "vgw-9a4cacf3",
          "VpcAttachments": []
      }
  }