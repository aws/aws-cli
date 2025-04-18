**To List Control Tower Enabled Controls**

The following ``list-enabled-controls`` example get details of AWS Control Tower enabled controls::

    aws controltower list-enabled-controls \
        --target-identifier arn:aws:organizations::123456789012:ou/o-s64ryxxxxx/ou-oqxx-i5wnxxxx

Output::

    {
        "enabledControls": [
            {
                "arn": "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/26RGJRSLXCP1KW8D",
                "controlIdentifier": "arn:aws:controltower:us-east-1::control/AWS-GR_CLOUDTRAIL_CHANGE_PROHIBITED",
                "driftStatusSummary": {
                    "driftStatus": "NOT_CHECKING"
                },
                "statusSummary": {
                    "status": "SUCCEEDED"
                },
                "targetIdentifier": "arn:aws:organizations::123456789012:ou/o-s64ryxxxxx/ou-oqxx-i5wnxxxx"
            },
            {
                "arn": "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/18AY24CWKM6IVSLU",
                "controlIdentifier": "arn:aws:controltower:us-east-1::control/AWS-GR_CLOUDTRAIL_CLOUDWATCH_LOGS_ENABLED",
                "driftStatusSummary": {
                    "driftStatus": "NOT_CHECKING"
                },
                "statusSummary": {
                    "status": "SUCCEEDED"
                },
                "targetIdentifier": "arn:aws:organizations::123456789012:ou/o-s64ryxxxxx/ou-oqxx-i5wnxxxx"
            }
        }
    }

For more information, see `AWS Control Tower Controls <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.