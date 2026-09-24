**To list all existing internet monitors**

The following ``list-monitors`` example lists all internet monitors. ::

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

For more information, see `Examples of using the CLI with Internet Monitor <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-IM-get-started-CLI.html#CloudWatch-IM-get-started-CLI-monitor-list>`__ in the *Amazon CloudWatch User Guide*.
