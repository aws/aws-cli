**To describe a recommendation for a component configuration**

The following example uses the ``describe-component-configuration-recommendation`` command to describe the recommended configuration for a component. ::

    aws application-insights describe-component-configuration-recommendation \
        --resource-group-name MYEC2 \
        --component-name arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56 \
        --tier DEFAULT

Output::

    {
        "ComponentConfiguration": "{\n  \"alarmMetrics\" : [ {\n    \"alarmMetricName\" : \"CPUUtilization\",\n    \"monitor\" : true\n  }, {\n    \"alarmMetricName\" : \"StatusCheckFailed\",\n    \"monitor\" : true\n  }, {\n    \"alarmMetricName\" : \"Processor % Processor Time\",\n    \"monitor\" : true\n  }, {\n    \"alarmMetricName\" : \"Memory % Committed Bytes In Use\",\n    \"monitor\" : true\n  }, {\n    \"alarmMetricName\" : \"LogicalDisk % Free Space\",\n    \"monitor\" : true\n  }, {\n    \"alarmMetricName\" : \"Memory Available Mbytes\",\n    \"monitor\" : true\n  } ],\n  \"logs\" : [ {\n    \"logGroupName\" : \"APPLICATION-MYEC2\",\n    \"logPath\" : \"\",\n    \"logType\" : \"APPLICATION\",\n    \"monitor\" : true,\n    \"encoding\" : \"utf-8\"\n  } ],\n  \"windowsEvents\" : [ {\n    \"logGroupName\" : \"WINDOWS_EVENTS-Application-MYEC2\",\n    \"eventName\" : \"Application\",\n    \"eventLevels\" : [ \"WARNING\", \"ERROR\", \"CRITICAL\" ],\n    \"monitor\" : true\n  }, {\n    \"logGroupName\" : \"WINDOWS_EVENTS-System-MYEC2\",\n    \"eventName\" : \"System\",\n    \"eventLevels\" : [ \"WARNING\", \"ERROR\", \"CRITICAL\" ],\n    \"monitor\" : true\n  }, {\n    \"logGroupName\" : \"WINDOWS_EVENTS-Security-MYEC2\",\n    \"eventName\" : \"Security\",\n    \"eventLevels\" : [ \"WARNING\", \"ERROR\", \"CRITICAL\" ],\n    \"monitor\" : true\n  } ],\n  \"subComponents\" : [ {\n    \"subComponentType\" : \"AWS::EC2::Volume\",\n    \"alarmMetrics\" : [ {\n      \"alarmMetricName\" : \"BurstBalance\",\n      \"monitor\" : true\n    } ]\n  } ]\n}"
    }