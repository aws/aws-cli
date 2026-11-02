**To accept ownership of a public virtual interface**

The following ``confirm-public-virtual-interface`` example accepts ownership of a public virtual interface created by another customer. ::

    aws directconnect confirm-public-virtual-interface \
        --virtual-interface-id dxvif-fg9xo9vp

Output::

    {
        "virtualInterfaceState": "verifying"
    }

For more information, see `Accept a hosted Direct Connect virtual interface <https://docs.aws.amazon.com/directconnect/latest/UserGuide/accepthostedvirtualinterface.html>`__ in the *AWS Direct Connect User Guide*.
