**To describe the configuration for a component**

This example uses the ``describe-component-configuration`` command to describe the configuration of the component. Note: The component name is the ARN of the component and not the resource's name. ::

    aws application-insights describe-component-configuration \
        --resource-group-name MYEC2 \
        --component-name arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56

Output::

    {
        "Monitor": true,
        "Tier": "DEFAULT",
        "ComponentConfiguration": "{\n  \"alarmMetrics\" : [ {\n    \"alarmMetricName\" : \"CPUUtilization\",\n    \"monitor\" : true\n  } ],\n  \"logs\" : [ ]\n}"
    }