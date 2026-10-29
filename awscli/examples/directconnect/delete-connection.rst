**To delete a connection**

The following ``delete-connection`` example deletes the specified connection. ::

    aws directconnect delete-connection \
        --connection-id dxcon-fg31dyv6

Output::

    {
        "ownerAccount": "123456789012",
        "connectionId": "dxcon-fg31dyv6",
        "connectionState": "deleted",
        "bandwidth": "1Gbps",
        "location": "TIVIT",
        "connectionName": "Connection to AWS",
        "region": "us-west-2"
    }

For more information, see `Delete a Direct Connect connection <https://docs.aws.amazon.com/directconnect/latest/UserGuide/deleteconnection.html>`__ in the *AWS Direct Connect User Guide*.
