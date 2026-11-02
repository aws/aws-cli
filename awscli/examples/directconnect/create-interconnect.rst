**To create an interconnect between a partner's network and AWS**

The following ``create-interconnect`` example creates an interconnect between an AWS Direct Connect partner's network and a specific AWS Direct Connect location. ::

    aws directconnect create-interconnect \
        --interconnect-name "1G Interconnect to AWS" \
        --bandwidth 1Gbps \
        --location TIVIT

Output::

    {
        "region": "us-west-2",
        "bandwidth": "1Gbps",
        "location": "TIVIT",
        "interconnectName": "1G Interconnect to AWS",
        "interconnectId": "dxcon-fgktov66",
        "interconnectState": "requested"
    }

For more information, see `Hosted Direct Connect connections <https://docs.aws.amazon.com/directconnect/latest/UserGuide/hosted_connection.html>`__ in the *AWS Direct Connect User Guide*.
