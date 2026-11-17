**To reset a Control Tower enabled baseline**

The following ``reset-enabled-baseline`` example resets an AWS Control Tower enabled baseline. ::

    aws controltower reset-enabled-baseline \
        --enabled-baseline-identifier arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XOM12BEL4YD578CQ2

Output::

    {
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Types of baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.
