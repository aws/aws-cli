**To tag a Control Tower enabled control**

The following ``tag-resource`` example tags an AWS Control Tower enabled control. ::

    aws controltower tag-resource \
        --resource-arn "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/2H2AWUG4SKG81855" \
        --tags "TestTagKey=TestTagValue"

This command produces no output.

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.