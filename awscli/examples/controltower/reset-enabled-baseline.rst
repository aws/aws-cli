**To Reset Control Tower Enabled Baseline**

The following ``reset-enabled-baseline`` example resets an AWS Control Tower enabled baseline::

    aws controltower reset-enabled-baseline \
        --enabled-baseline-identifier arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XOM12BEL4YD578CQ2

Output::

    {
        "operationIdentifier": "214cde95-5c39-46b9-b429-4fad550a7096"
    }

For more information, see `AWS Control Tower Baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.