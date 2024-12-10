**To list the tags associated with an internet monitor**

This example uses the ``list-tags-for-resource`` command to list the available tags associated with an internet monitor. ::

    aws internetmonitor list-tags-for-resource \
        --resource-arn arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor

Output::

    {
        "Tags": {
            "Environment": "Prod",
            "Type": "App"
        }
    }