**To remove tags from an internet monitor**

This example uses the ``untag-resource`` command to remove one or more tags from an internet monitor. ::

    aws internetmonitor untag-resource \
        --resource-arn arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor \
        --tag-keys Environment Type

This command returns to the prompt if successful.