**To list Control Tower enabled baselines**

The following ``list-enabled-baselines`` example lists all enabled AWS Control Tower baselines. ::

    aws controltower list-enabled-baselines

Output::

    {
        "enabledBaselines": [
            {
                "arn": "arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XAJNZNCBC1I386C7B",
                "baselineIdentifier": "arn:aws:controltower:us-east-1::baseline/LN25R72TTG6IGPTQ",
                "statusSummary": {
                    "status": "SUCCEEDED"
                },
                "targetIdentifier": "arn:aws:organizations::123456789012:account/o-3onqfuxxxx/123456789012"
            },
            {
                "arn": "arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XAH3ZJL9DWA386CA5",
                "baselineIdentifier": "arn:aws:controltower:us-east-1::baseline/4T4HA1KMO10S6311",
                "statusSummary": {
                    "status": "SUCCEEDED"
                },
                "targetIdentifier": "arn:aws:organizations::123456789012:account/o-3onqfuxxxx/012345098765"
            },
            {
                "arn": "arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XALFJ9548TL386CBT",
                "baselineIdentifier": "arn:aws:controltower:us-east-1::baseline/J8HX46AHS5MIKQPD",
                "statusSummary": {
                    "status": "SUCCEEDED"
                },
                "targetIdentifier": "arn:aws:organizations::123456789012:account/o-3onqfuxxxx/098765432109"
            }
        ]
    }

For more information, see `Types of baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.