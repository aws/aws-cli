**To list all connections in the current region**

The following ``describe-connections`` command lists all connections in the current region::

  aws directconnect describe-connections

Output::

  {
      "connections": [
          {
              "ownerAccount": "123456789012", 
              "connectionId": "dxcon-fg31dyv6", 
              "connectionState": "requested", 
              "bandwidth": "1Gbps", 
              "location": "TIVIT", 
              "connectionName": "Connection to AWS", 
              "region": "sa-east-1"
          }
      ]
  }