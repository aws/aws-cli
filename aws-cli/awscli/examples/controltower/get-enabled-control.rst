**To get a Control Tower enabled control**

The following ``get-enabled-control`` example gets details of an AWS Control Tower enabled control. ::

    aws controltower get-enabled-control \
        --enabled-control-identifier arn:aws:controltower:us-west-2:123456789012:enabledcontrol/26RGJRSLXCP1KW8D

Output::

    {
        "enabledControlDetails": {
            "arn": "arn:aws:controltower:us-west-2:123456789012:enabledcontrol/26RGJRSLXCP1KW8D",
            "controlIdentifier": "arn:aws:controltower:us-west-2::control/AWS-GR_CLOUDTRAIL_CHANGE_PROHIBITED",
            "driftStatusSummary": {
                "driftStatus": "NOT_CHECKING"
            },
            "parameters": [],
            "statusSummary": {
                "status": "SUCCEEDED"
            },
            "targetIdentifier": "arn:aws:organizations::123456789012:ou/o-s64ryixxxx/ou-oqxx-i5wnxxxx",
            "targetRegions": [
                {
                    "name": "us-west-2"
                }
            ]
        }
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.
