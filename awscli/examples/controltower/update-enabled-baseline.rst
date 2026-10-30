**Example 1: To update a disabled Control Tower baseline**

The following ``update-enabled-baseline`` example updates an AWS Control Tower enabled baseline if baseline 'IdentityCenterBaseline' is disabled. ::

    aws controltower update-enabled-baseline \
        --baseline-version 4.0 \
        --enabled-baseline-identifier arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XOM12BEL4YD578CQ2

Output::

    {
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

**Example 2: To update an enabled Control Tower baseline**

The following ``update-enabled-baseline`` example updates an AWS Control Tower enabled baseline if baseline 'IdentityCenterBaseline' is enabled. ::

    aws controltower update-enabled-baseline \
        --baseline-version 4.0 \
        --enabled-baseline-identifier arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XOM12BEL4YD578CQ2 \
        --parameters '[{"key":"IdentityCenterEnabledBaselineArn","value":"arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XAJNZNCBC1I386C7B"}]'

Output::

    {
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Types of baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.
