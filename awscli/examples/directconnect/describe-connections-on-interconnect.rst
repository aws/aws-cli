**To list connections on an interconnect**

The following ``describe-connections-on-interconnect`` example lists connections that have been provisioned on the given interconnect. ::

    aws directconnect describe-connections-on-interconnect \
        --interconnect-id dxcon-fgktov66

Output::

    {
        "connections": [
            {
                "partnerName": "TIVIT",
                "vlan": 101,
                "ownerAccount": "123456789012",
                "connectionId": "dxcon-ffzc51m1",
                "connectionState": "ordering",
                "bandwidth": "500Mbps",
                "location": "TIVIT",
                "connectionName": "mydcinterconnect",
                "region": "us-west-2"
            }
        ]
    }

For more information, see `Hosted Direct Connect connections <https://docs.aws.amazon.com/directconnect/latest/UserGuide/hosted_connection.html>`__ in the *AWS Direct Connect User Guide*.
