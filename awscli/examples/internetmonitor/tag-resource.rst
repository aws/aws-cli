**To add tags to an internet monitor**

This example uses the ``tag-resource`` command to add one or more tags to an internet monitor. ::

    aws internetmonitor tag-resource \
        --resource-arn arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor \
        --tags Environment=Prod,Type=App

This command returns to the prompt if successful.