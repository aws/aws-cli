**To update an existing internet monitor**

This example uses the ``update-monitor`` command to update an existing internet monitor to monitor an additional resource. ::

    aws internetmonitor update-monitor \
        --monitor-name TestMonitor \
        --resources-to-add arn:aws:ec2:us-east-1:123456789012:vpc/vpc-345678defghi

Output::

    {
        "MonitorArn": "arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor",
        "Status": "PENDING"
    }