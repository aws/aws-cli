**To delete a LAG**

The following ``delete-lag`` example deletes the specified LAG. ::

    aws directconnect delete-lag \
        --lag-id dxlag-ffrhowd9

Output::

    {
        "awsDevice": "EqDC2-4h6ce2r1bes6",
        "numberOfConnections": 0,
        "lagState": "deleted",
        "ownerAccount": "123456789012",
        "lagName": "TestLAG",
        "connections": [],
        "lagId": "dxlag-ffrhowd9",
        "minimumLinks": 0,
        "connectionsBandwidth": "1Gbps",
        "region": "us-west-2",
        "location": "EqDC2"
    }

For more information, see `Delete a Direct Connect endpoint LAG <https://docs.aws.amazon.com/directconnect/latest/UserGuide/delete-lag.html>`__ in the *AWS Direct Connect User Guide*.
