**To describe an existing internet monitor**

This example uses the ``get-monitor`` command to describe the configuration of an existing internet monitor. ::

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