**To disassociate a connection from a LAG**

The following ``disassociate-connection-from-lag`` example disassociates the specified connection from the specified LAG. ::

    aws directconnect disassociate-connection-from-lag \
        --lag-id dxlag-fhccu14t \
        --connection-id dxcon-fg9607vm

Output::

    {
        "ownerAccount": "123456789012",
        "connectionId": "dxcon-fg9607vm",
        "connectionState": "requested",
        "bandwidth": "1Gbps",
        "location": "EqDC2",
        "connectionName": "Con2ForLag",
        "region": "us-west-2"
    }

For more information, see `Disassociate a connection from a LAG at a Direct Connect endpoint <https://docs.aws.amazon.com/directconnect/latest/UserGuide/disassociate-connection-from-lag.html>`__ in the *AWS Direct Connect User Guide*.
