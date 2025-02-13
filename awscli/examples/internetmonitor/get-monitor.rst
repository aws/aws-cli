**To describe an existing internet monitor**

The following ``get-monitor`` example describes the configuration of an existing internet monitor. ::

    aws internetmonitor get-monitor \
        --monitor-name TestMonitor

Output::

    {
        "MonitorName": "TestMonitor",
        "MonitorArn": "arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor",
        "Resources": ["arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123456abcdef"],
        "Status": "ACTIVE",
        "CreatedAt": "2024-08-28T20:10:18+00:00",
        "ModifiedAt": "2024-08-28T20:10:18+00:00",
        "ProcessingStatus": "COLLECTING_DATA",
        "ProcessingStatusInfo": "The monitor is OK and is collecting data-points to produce insights",
        "Tags": {},
        "InternetMeasurementsLogDelivery": {},
        "TrafficPercentageToMonitor": 100
    }

For more information, see `Use a monitor in Internet Monitor <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/IMWhyCreateMonitor.html>`__ in the *Amazon CloudWatch User Guide*.
