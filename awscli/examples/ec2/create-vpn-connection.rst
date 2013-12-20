**To create a VPN connection with dynamic routing**

This example creates a VPN connection between the specified virtual private gateway and the specified customer gateway. The output includes the configuration information that your network administrator needs, in XML format.

Command::

  aws ec2 create-vpn-connection --type ipsec.1 --customer-gateway-id cgw-0e11f167 --vpn-gateway-id vgw-9a4cacf3

Output::

  {
      "VpnConnection": {
          "VpnConnectionId": "vpn-40f41529"
          "CustomerGatewayConfiguration": "...configuration information...",
          "State": "available",
          "VpnGatewayId": "vgw-f211f09b",
          "CustomerGatewayId": "cgw-b4de3fdd"
      }
  }
  
**To create a VPN connection with static routing**

This example creates a VPN connection between the specified virtual private gateway and the specified customer gateway. The options specify static routing. The output includes the configuration information that your network administrator needs, in XML format.

Command::

  aws ec2 create-vpn-connection --type ipsec.1 --customer-gateway-id cgw-0e11f167 --vpn-gateway-id vgw-9a4cacf3 --options "{\"StaticRoutesOnly\":true}"

Output::

  {
      "VpnConnection": {
          "VpnConnectionId": "vpn-40f41529"
          "CustomerGatewayConfiguration": "...configuration information...",
          "State": "pending",
          "VpnGatewayId": "vgw-f211f09b",
          "CustomerGatewayId": "cgw-b4de3fdd",
          "Options": {
              "StaticRoutesOnly": true
          }          
      }
  }