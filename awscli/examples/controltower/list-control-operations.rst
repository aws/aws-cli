**To list Control Tower control operations**

The following ``list-control-operations`` example lists details of AWS Control Tower controls in progress or queued. ::

    aws controltower list-control-operations

Output::

    {
        "controlOperations": [
            {
                "startTime": "2024-02-19T19:22:08+00:00",
                "operationType": "ENABLE_CONTROL",
                "status": "IN_PROGRESS",
                "statusMessage": "Operation is in progress.",
                "operationIdentifier": "f9f43b45-db27-44df-89d8-f9129e3632XX",
                "controlIdentifier": "arn:aws:controltower:us-east-1::control/SKIBWKYUQAAC",
                "targetIdentifier": "arn:aws:organizations::123456789012:ou/o-yy67i3pfv2/ou-slt4-8abknXXX",
                "enabledControlIdentifier": "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/RWZFSHV2BBRU6JSE"
            },
            {
                "startTime": "2024-02-19T19:21:09+00:00",
                "operationType": "ENABLE_CONTROL",
                "status": "IN_PROGRESS",
                "statusMessage": "Operation is in progress."
                "operationIdentifier": "171ee0b1-e926-486e-9775-005bd244ccXX",
                "controlIdentifier": "arn:aws:controltower:us-east-1::control/PDKYAANJEWJE",
                "targetIdentifier": "arn:aws:organizations::123456789012:ou/o-yy67i3pfv2/ou-slt4-fl6miXXX",
                "enabledControlIdentifier": "arn:aws:controltower:us-east-2:123456789012:enabledcontrol/XCNJARWZFSHV6JSE"
            }
        ]
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.