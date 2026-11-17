**To accept ownership of a transit virtual interface**

The following ``confirm-transit-virtual-interface`` example accepts ownership of a transit virtual interface created by another customer. ::

    aws directconnect confirm-transit-virtual-interface \
        --virtual-interface-id dxvif-fEXAMPLE \
        --direct-connect-gateway-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "virtualInterfaceState": "pending"
    }

For more information, see `Accepting a Hosted Virtual Interface <https://docs.aws.amazon.com/directconnect/latest/UserGuide/accepthostedvirtualinterface.html>`__ in the *AWS Direct Connect User Guide*.
