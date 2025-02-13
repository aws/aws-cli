**To list the tags associated with an internet monitor**

The following ``list-tags-for-resource`` example lists the available tags associated with an internet monitor. ::

    aws internetmonitor list-tags-for-resource \
        --resource-arn arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor

Output::

    {
        "Tags": {
            "Environment": "Prod",
            "Type": "App"
        }
    }

For more information, see `Tagging your Amazon CloudWatch resources <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Tagging.html>`__ in the *Amazon CloudWatch User Guide*.
