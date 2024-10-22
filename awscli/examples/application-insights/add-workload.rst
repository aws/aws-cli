**To add a workload to a component**

This example uses the ``add-workload`` command to add a workload to a component. ::

    aws application-insights add-workload \
        --resource-group-name "sqlserver" \
        --component-name "arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56" \
        --workload-configuration file://workload.json

Contents of ``workload.json``::

    {
        "WorkloadName": "SQL",
        "Tier": "SQL_SERVER",
        "Configuration": "{\"logs\":[{\"logGroupName\":\"SQL_SERVER-sqlserver\",\"logPath\":\"/var/log/mysql\",\"logType\":\"MYSQL\",\"monitor\":true,\"encoding\":\"utf-16\"}]}"
    }

Output::

    {
        "WorkloadId": "w-0123fb74-fb3b-4dc8-b6cc-aab404a1234",
        "WorkloadConfiguration": {
            "WorkloadName": "SQL",
            "Tier": "SQL_SERVER",
            "Configuration": "{\"logs\":[{\"logGroupName\":\"SQL_SERVER-sqlserver\",\"logPath\":\"/var/log/mysql\",\"logType\":\"MYSQL\",\"monitor\":true,\"encoding\":\"utf-16\"}]}"
        }
    }
