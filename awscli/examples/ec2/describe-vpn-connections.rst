**To describe your VPN connections**

This example describes your VPN connections.

Command::

  aws ec2 describe-vpn-connections

Output::

  {
      "VpnConnections": {
          "VpnConnectionId": "vpn-40f41529"
          "CustomerGatewayConfiguration": "...configuration information...",
          "VgwTelemetry": [
              {
                  "Status": "DOWN",
                  "AcceptedRouteCount": 0,
                  "OutsideIpAddress": "72.21.209.192",
                  "LastStatusChange": "2013-02-04T20:19:34.000Z",
                  "StatusMessage": "IPSEC IS DOWN"
              },
              {
                  "Status": "DOWN",
                  "AcceptedRouteCount": 0,
                  "OutsideIpAddress": "72.21.209.224",
                  "LastStatusChange": "2013-02-04T20:19:34.000Z",
                  "StatusMessage": "IPSEC IS DOWN"
              }
          ],
          "State": "available",
          "VpnGatewayId": "vgw-9a4cacf3",
          "CustomerGatewayId": "cgw-0e11f167"
          "Type": "ipsec.1"
      }
  }
  
**To describe your available VPN connections**

This example describes your VPN connections with a state of ``available``.

Command::

  aws ec2 describe-vpn-connections --filters "Name=state,Values=available"
