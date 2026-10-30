**To decommission a landing zone**

The following ``delete-landing-zone`` example decommissions the AWS Control Tower landing zone. ::

    aws controltower delete-landing-zone \
        --landing-zone-identifier arn:aws:controltower:us-west-2:123456789012:landingzone/13CJG46WZKXXX4X5

Output::

    {
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Decommission an AWS Control Tower landing zone <https://docs.aws.amazon.com/controltower/latest/userguide/decommission-landing-zone.html>`__ in the *AWS Control Tower User Guide*.
