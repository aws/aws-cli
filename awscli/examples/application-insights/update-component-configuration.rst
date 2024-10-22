**To update a component configuration**

This example uses the ``update-component-configuration`` command to update a component configuration to monitor a Metric. ::

    aws application-insights update-component-configuration \
        --resource-group-name ASG \
        --component-name arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56 \
        --component-configuration file://config.json

Contents of ``config.json``::

    {
        "logs": [],
        "alarmMetrics": [{
            "alarmMetricName": "CPUUtilization",
            "monitor": true
        }]
    }

This command returns to the prompt if successful.