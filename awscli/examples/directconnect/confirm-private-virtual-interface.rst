**To accept ownership of a private virtual interface**

The following ``confirm-private-virtual-interface`` example accepts ownership of a private virtual interface created by another customer. ::

    aws directconnect confirm-private-virtual-interface \
        --virtual-interface-id dxvif-fgy8orxu \
        --virtual-gateway-id vgw-e4a47df9

Output::

    {
        "virtualInterfaceState": "pending"
    }

For more information, see `Accept a hosted Direct Connect virtual interface <https://docs.aws.amazon.com/directconnect/latest/UserGuide/accepthostedvirtualinterface.html>`__ in the *AWS Direct Connect User Guide*.
