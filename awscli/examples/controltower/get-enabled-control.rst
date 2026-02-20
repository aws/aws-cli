**To get a Control Tower enabled control**

The following ``get-enabled-control`` example get details of an AWS Control Tower enabled control. ::

    aws controltower get-enabled-control \
        --enabled-control-identifier arn:aws:controltower:us-east-1:123456789012:enabledcontrol/26RGJRSLXCP1KW8D

Output::

    {
        "enabledControlDetails": {
            "arn": "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/26RGJRSLXCP1KW8D",
            "controlIdentifier": "arn:aws:controltower:us-east-1::control/AWS-GR_CLOUDTRAIL_CHANGE_PROHIBITED",
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
                    "name": "ap-south-2"
                },
                {
                    "name": "ap-south-1"
                },
                {
                    "name": "eu-south-1"
                },
                {
                    "name": "us-east-1"
                }
            ]
        }
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.