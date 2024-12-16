**To create a new internet monitor**

This example uses the ``create-monitor`` command to create a new internet monitor. ::

    aws internetmonitor create-monitor \
        --monitor-name TestMonitor \
        --resources arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123456abcdef \
        --traffic-percentage-to-monitor 100 \
        --internet-measurements-log-delivery S3Config={LogDeliveryStatus=DISABLED} 

Output::

    {
        "Arn": "arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor",
        "Status": "PENDING"
    }