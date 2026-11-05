**To create a connection from your network to an AWS Direct Connect location**

The following ``create-connection`` example creates a connection from your network to an AWS Direct Connect location. ::

    aws directconnect create-connection \
        --location TIVIT \
        --bandwidth 1Gbps \
        --connection-name "Connection to AWS"

Output::

    {
        "ownerAccount": "123456789012",
        "connectionId": "dxcon-fg31dyv6",
        "connectionState": "requested",
        "bandwidth": "1Gbps",
        "location": "TIVIT",
        "connectionName": "Connection to AWS",
        "region": "us-west-2"
    }

For more information, see `Dedicated Direct Connect connections <https://docs.aws.amazon.com/directconnect/latest/UserGuide/dedicated_connection.html>`__ in the *AWS Direct Connect User Guide*.
