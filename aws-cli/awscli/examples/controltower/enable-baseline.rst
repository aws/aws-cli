**Example 1: To enable a Control Tower baseline that is disabled**

The following ``enable-baseline`` example enables an AWS Control Tower baseline if baseline ``IdentityCenterBaseline`` is disabled. ::

    aws controltower enable-baseline \
        --baseline-identifier arn:aws:controltower:us-west-2::baseline/17BSJV3IGJ2QSGA2 \
        --baseline-version 4.0 \
        --target-identifier arn:aws:organizations::123456789012:ou/o-s64ryixxxx/ou-oq9f-i5wnxxxx

Output::

    {
        "arn": "arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XOM12BEL4YD578CQ2",
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Types of baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.

**Example 2: To enable a Control Tower baseline that is enabled**

The following ``enable-baseline`` example enables an AWS Control Tower baseline if baseline ``IdentityCenterBaseline`` is enabled. ::

    aws controltower enable-baseline \
        --baseline-identifier arn:aws:controltower:us-west-2::baseline/17BSJV3IGJ2QSGA2 \
        --baseline-version 4.0 \
        --target-identifier arn:aws:organizations::123456789012:ou/o-s64ryixxxx/ou-oqxx-i5wnxxxx \
        --parameters '[{"key":"IdentityCenterEnabledBaselineArn","value":"arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XAJNZNCBC1I386C7B"}]'

Output::

    {
        "arn": "arn:aws:controltower:us-west-2:123456789012:enabledbaseline/XOM12BEL4YD578CQ2",
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Types of baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.
