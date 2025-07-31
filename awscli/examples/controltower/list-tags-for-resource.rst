**To List Tags for Control Tower Enabled Control**

The following ``list-tags-for-resource`` example lists the tags for AWS Control Tower Enabled Controls::

    aws controltower list-tags-for-resource \
        --resource-arn "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/2H2AWUG4SKG81855"

Output::

    {
        "tags": {
            "TestTagKey": "TestTagValue"
        }
    }

For more information, see `AWS Control Tower Controls <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.