**To add tags to an internet monitor**

The following ``tag-resource`` example adds one or more tags to an internet monitor. ::

    aws internetmonitor tag-resource \
        --resource-arn arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor \
        --tags Environment=Prod,Type=App

This command produces no output.

For more information, see `Tagging your Amazon CloudWatch resources <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Tagging.html>`__ in the *Amazon CloudWatch User Guide*.
