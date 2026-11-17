**To reset a Control Tower landing zone**

The following ``reset-landing-zone`` example resets a AWS Control Tower landing zone. ::

    aws controltower reset-landing-zone \
        --landing-zone-identifier arn:aws:controltower:us-west-2:123456789012:landingzone/13CJG46WZKXXX4X5

Output::

    {
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Getting started with AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.
