**To list interconnects**

The following ``describe-interconnects`` example lists the interconnects owned by your AWS account. ::

    aws directconnect describe-interconnects

Output::

    {
        "interconnects": [
            {
                "region": "us-west-2",
                "bandwidth": "1Gbps",
                "location": "TIVIT",
                "interconnectName": "1G Interconnect to AWS",
                "interconnectId": "dxcon-fgktov66",
                "interconnectState": "down"
            }
        ]
    }

For more information, see `Direct Connect dedicated and hosted connections <https://docs.aws.amazon.com/directconnect/latest/UserGuide/WorkingWithConnections.html>`__ in the *AWS Direct Connect User Guide*.
