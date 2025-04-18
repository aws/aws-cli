**To Update Control Tower Enabled Baseline**

The following ``update-enabled-baseline`` example updates an AWS Control Tower enabled baseline if baseline 'IdentityCenterBaseline' is **not** enabled::

    aws controltower update-enabled-baseline \
        --baseline-version 4.0 \
        --enabled-baseline-identifier arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XOM12BEL4YD578CQ2

Output::

    {
        "operationIdentifier": "214cde95-5c39-46b9-b429-4fad550a7096"
    }

The following ``update-enabled-baseline`` example updates an AWS Control Tower enabled baseline if baseline 'IdentityCenterBaseline' is enabled::

    aws controltower update-enabled-baseline \
        --baseline-version 4.0 \
        --enabled-baseline-identifier arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XOM12BEL4YD578CQ2 \
        --parameters '[{"key":"IdentityCenterEnabledBaselineArn","value":"arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XAJNZNCBC1I386C7B"}]'

Output::

    {
        "operationIdentifier": "b0f4a7c2-334d-48d9-971e-47fea9db3e8b"
    }

For more information, see `AWS Control Tower Baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.