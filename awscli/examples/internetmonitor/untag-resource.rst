**To remove tags from an internet monitor**

The following ``untag-resource`` example removes one or more tags from an internet monitor. ::

    aws internetmonitor untag-resource \
        --resource-arn arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor \
        --tag-keys Environment Type

This command produces no output.

For more information, see `Tagging your Amazon CloudWatch resources <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Tagging.html>`__ in the *Amazon CloudWatch User Guide*.
