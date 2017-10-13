**To create a VPN connection with dynamic routing**

This example creates a VPN connection between the specified virtual private gateway and the specified customer gateway. The output includes the configuration information that your network administrator needs, in XML format.

Command::

  aws ec2 create-vpn-connection --type ipsec.1 --customer-gateway-id cgw-0e11f167 --vpn-gateway-id vgw-9a4cacf3

Output::

  {
      "VpnConnection": {
          "VpnConnectionId": "vpn-1a2b3c4d"
          "CustomerGatewayConfiguration": "...configuration information...",
          "State": "available",
          "VpnGatewayId": "vgw-9a4cacf3",
          "CustomerGatewayId": "cgw-0e11f167"
      }
  }
  
**To create a VPN connection with static routing**

This example creates a VPN connection between the specified virtual private gateway and the specified customer gateway. The options specify static routing. The output includes the configuration information that your network administrator needs, in XML format.

Command::

  aws ec2 create-vpn-connection --type ipsec.1 --customer-gateway-id cgw-1a1a1a1a --vpn-gateway-id vgw-9a4cacf3 --options "{\"StaticRoutesOnly\":true}"

Output::

  {
      "VpnConnection": {
          "VpnConnectionId": "vpn-11aa33cc"
          "CustomerGatewayConfiguration": "...configuration information...",
          "State": "pending",
          "VpnGatewayId": "vgw-9a4cacf3",
          "CustomerGatewayId": "cgw-1a1a1a1a",
          "Options": {
              "StaticRoutesOnly": true
          }          
      }
  }

**To create a VPN connection and specify your own inside CIDR and pre-shared key**

This example creates a VPN connection and specifies the inside IP address CIDR block and a custom pre-shared key for each tunnel. The specified values are returned in the ``CustomerGatewayConfiguration`` information.

Command::

  aws ec2 create-vpn-connection --type ipsec.1 --customer-gateway-id cgw-b4de3fdd --vpn-gateway-id vgw-f211f09b --options "{"StaticRoutesOnly":false,"TunnelOptions":[{"TunnelInsideCidr":"169.254.12.0/30","PreSharedKey":"ExamplePreSharedKey1"},{"TunnelInsideCidr":"169.254.13.0/30","PreSharedKey":"ExamplePreSharedKey2"}]}"

Output::

  {
      "VpnConnection": {
          "VpnConnectionId": "vpn-40f41529"
          "CustomerGatewayConfiguration": "...configuration information...",
          "State": "pending",
          "VpnGatewayId": "vgw-f211f09b",
          "CustomerGatewayId": "cgw-b4de3fdd"
      }
  }
