**To describe your LAGs**

The following ``describe-lags`` example describes all of your LAGs for the current region. ::

    aws directconnect describe-lags

Output::

    {
        "lags": [
            {
                "awsDevice": "EqDC2-19y7z3m17xpuz",
                "numberOfConnections": 2,
                "lagState": "down",
                "ownerAccount": "123456789012",
                "lagName": "DA-LAG",
                "connections": [
                    {
                        "ownerAccount": "123456789012",
                        "connectionId": "dxcon-ffnikghc",
                        "lagId": "dxlag-fgsu9erb",
                        "connectionState": "requested",
                        "bandwidth": "10Gbps",
                        "location": "EqDC2",
                        "connectionName": "Requested Connection 1 for Lag dxlag-fgsu9erb",
                        "region": "us-west-2"
                    },
                    {
                        "ownerAccount": "123456789012",
                        "connectionId": "dxcon-fglgbdea",
                        "lagId": "dxlag-fgsu9erb",
                        "connectionState": "requested",
                        "bandwidth": "10Gbps",
                        "location": "EqDC2",
                        "connectionName": "Requested Connection 2 for Lag dxlag-fgsu9erb",
                        "region": "us-west-2"
                    }
                ],
                "lagId": "dxlag-fgsu9erb",
                "minimumLinks": 0,
                "connectionsBandwidth": "10Gbps",
                "region": "us-west-2",
                "location": "EqDC2"
            }
        ]
    }

For more information, see `View LAG details at a Direct Connect endpoint <https://docs.aws.amazon.com/directconnect/latest/UserGuide/view-lag.html>`__ in the *AWS Direct Connect User Guide*.
