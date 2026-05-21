**To disable a Control Tower baseline**

The following ``disable-baseline`` example disables an AWS Control Tower baseline. ::

    aws controltower disable-baseline \
        --enabled-baseline-identifier arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XOM12BEL4YD578CQ2

Output::

    {
        "operationIdentifier": "b33486d7-5396-4ad0-9eae-3a57969fe8cd"
    }

For more information, see `Types of baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.
