**To get a Control Tower enabled baseline**

The following ``get-enabled-baseline`` example gets details of an AWS Control Tower enabled baseline. ::

    aws controltower get-enabled-baseline \
        --enabled-baseline-identifier arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XOM12BEL4YD578CQ2

Output::

    {
        "enabledBaselineDetails": {
            "arn": "arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XOM12BEL4YD578CQ2",
            "baselineIdentifier": "arn:aws:controltower:us-west-2::baseline/17BSJV3IGJ2QSGA2",
            "baselineVersion": "4.0",
            "parameters": [
                {
                    "key": "IdentityCenterEnabledBaselineArn",
                    "value": "arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XAJNZNCBC1I386C7B"
                }
            ],
            "statusSummary": {
                "lastOperationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "status": "SUCCEEDED"
            },
            "targetIdentifier": "arn:aws:organizations::123456789012:ou/o-3onqfufxxx/ou-g8xx-5kluxxxx"
        }
    }

For more information, see `Types of baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.
