**To list all existing internet monitors**

This example uses the ``list-monitors`` command to list all internet monitors. ::

    aws internetmonitor list-monitors

Output::

    {
        "Monitors": [{
            "MonitorName": "TestMonitor",
            "MonitorArn": "arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor",
            "Status": "ACTIVE",
            "ProcessingStatus": "OK"
        }]
    }