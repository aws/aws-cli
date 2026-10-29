**To create a monitor**

The following ``create-monitor`` example creates a monitor named ``demo`` in the specified account. ::

    aws networkflowmonitor create-monitor \
        --monitor-name demo \
        --local-resources type="AWS::EC2::VPC",identifier="arn:aws:ec2:us-west-2:123456789012:vpc/vpc-03ea55eeda25adbb0"  \
        --scope-arn arn:aws:networkflowmonitor:us-west-2:123456789012:scope/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "monitorArn": "arn:aws:networkflowmonitor:us-west-2:123456789012:monitor/demo",
        "monitorName": "demo",
        "monitorStatus": "ACTIVE",
        "tags": {}
    }

For more information, see `Create a monitor in Network Flow Monitor <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-NetworkFlowMonitor-configure-monitors-create.html>`__ in the *Amazon CloudWatch User Guide*.