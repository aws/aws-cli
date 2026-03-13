**To list tags for Control Tower enabled controls**

The following ``list-tags-for-resource`` example lists the tags for AWS Control Tower Enabled Controls. ::

    aws controltower list-tags-for-resource \
        --resource-arn "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/2H2AWUG4SKG81855"

Output::

    {
        "tags": {
            "TestTagKey": "TestTagValue"
        }
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.