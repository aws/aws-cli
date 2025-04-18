**To Get Control Tower Control Operations**

The following ``get-control-operation`` example get details of an AWS Control Tower control operation::

    aws controltower get-control-operation \
        --operation-identifier "7691fc5a-de87-4540-8c95-b0aabd56382c"

Output::

    {
        "controlOperation": {
            "controlIdentifier": "arn:aws:controlcatalog:::control/497wrm2xnk1wxlf4obrdo7mej",
            "enabledControlIdentifier": "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/18J5KBJ3W3VTIRLV",
            "endTime": "2025-04-17T03:08:55+00:00",
            "operationIdentifier": "7691fc5a-de87-4540-8c95-b0aabd56382c",
            "operationType": "ENABLE_CONTROL",
            "startTime": "2025-04-17T03:07:52+00:00",
            "status": "SUCCEEDED",
            "statusMessage": "Operation was successful.",
            "targetIdentifier": "arn:aws:organizations::123456789012:ou/o-s64ryixxxx/ou-oqxx-i5wnxxxx"
        }
    }

For more information, see `AWS Control Tower Controls <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.