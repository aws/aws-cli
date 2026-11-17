**To update a Control Tower enabled control**

The following ``update-enabled-control`` example updates an AWS Control Tower enabled control. ::

    aws controltower update-enabled-control \
        --enabled-control-identifier arn:aws:controltower:us-west-2:123456789012:enabledcontrol/JSJN8UL0G2MWGRTZ \
        --parameters '[{"key":"AllowedRegions","value":["us-east-1","us-west-1","us-west-2","us-east-2"]}]'

Output::

    {
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.
