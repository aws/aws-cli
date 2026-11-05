**To associate a connection with a LAG**

The following ``associate-connection-with-lag`` example associates the specified connection with the specified LAG. ::

    aws directconnect associate-connection-with-lag \
        --lag-id dxlag-fhccu14t \
        --connection-id dxcon-fg9607vm

Output::

    {
        "ownerAccount": "123456789012",
        "connectionId": "dxcon-fg9607vm",
        "lagId": "dxlag-fhccu14t",
        "connectionState": "requested",
        "bandwidth": "1Gbps",
        "location": "EqDC2",
        "connectionName": "Con2ForLag",
        "region": "us-west-2"
    }

For more information, see `Associate a connection with a LAG at a Direct Connect endpoint <https://docs.aws.amazon.com/directconnect/latest/UserGuide/associate-connection-with-lag.html>`__ in the *AWS Direct Connect User Guide*.
