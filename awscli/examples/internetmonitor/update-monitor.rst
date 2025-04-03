**To update an existing internet monitor**

The following ``update-monitor`` example updates an existing internet monitor to monitor an additional resource. ::

    aws internetmonitor update-monitor \
        --monitor-name TestMonitor \
        --resources-to-add arn:aws:ec2:us-east-1:123456789012:vpc/vpc-345678defghi

Output::

    {
        "MonitorArn": "arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor",
        "Status": "PENDING"
    }

For more information, see `Edit a monitor in Internet Monitor <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-IM-get-started.edit-monitor.html>`__ in the *Amazon CloudWatch User Guide*.
