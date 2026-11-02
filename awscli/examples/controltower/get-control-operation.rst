**To get Control Tower control operations**

The following ``get-control-operation`` example gets details of an AWS Control Tower control operation. ::

    aws controltower get-control-operation \
        --operation-identifier "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "controlOperation": {
            "controlIdentifier": "arn:aws:controlcatalog:::control/497wrm2xnk1wxlf4obrdo7mej",
            "enabledControlIdentifier": "arn:aws:controltower:us-west-2:123456789012:enabledcontrol/18J5KBJ3W3VTIRLV",
            "endTime": "2025-04-17T03:08:55+00:00",
            "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "operationType": "ENABLE_CONTROL",
            "startTime": "2025-04-17T03:07:52+00:00",
            "status": "SUCCEEDED",
            "statusMessage": "Operation was successful.",
            "targetIdentifier": "arn:aws:organizations::123456789012:ou/o-s64ryixxxx/ou-oqxx-i5wnxxxx"
        }
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.
