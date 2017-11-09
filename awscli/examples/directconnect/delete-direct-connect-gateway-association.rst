**To delete a Direct Connect gateway association**

The following example disassociates virtual private gateway ``vgw-6efe725e`` from Direct Connect gateway ``5f294f92-bafb-4011-916d-9b0bexample``.

Command::

  aws directconnect delete-direct-connect-gateway-association --direct-connect-gateway-id 5f294f92-bafb-4011-916d-9b0bexample --virtual-gateway-id vgw-6efe725e

Output::

  {
    "directConnectGatewayAssociation": {
        "associationState": "disassociating", 
        "virtualGatewayOwnerAccount": "123456789012", 
        "directConnectGatewayId": "5f294f92-bafb-4011-916d-9b0bexample", 
        "virtualGatewayId": "vgw-6efe725e", 
        "virtualGatewayRegion": "us-east-2"
    }
  }