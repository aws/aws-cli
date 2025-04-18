**To Untag Control Tower Enabled Control**

The following ``untag-resource`` example untags an AWS Control Tower enabled control::

    aws controltower untag-resource \
        --resource-arn "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/2H2AWUG4SKG81855" \
        --tag-keys "TestTagKey"


For more information, see `AWS Control Tower Controls <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.