**To update a workload in an component**

This example uses the ``update-workload`` command to update the workload of a component. ::

    aws application-insights update-workload \
        --resource-group-name sqlserver \
        --component-name arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56 \
        --workload-configuration file://update.json \
        --workload-id w-765437d7-51e1-438e-8f47-123456fb

Contents of ``update.json``::

    {
        "WorkloadName": "MYSQL",
        "Tier": "MYSQL",
        "Configuration": "{\"logs\":[{\"logGroupName\":\"MYSQL\",\"logPath\":\"/var/log/**\",\"logType\":\"MYSQL\",\"monitor\":true,\"encoding\":\"utf-8\"}]}"
    }

Output::

    {
        "WorkloadId": "w-765437d7-51e1-438e-8f47-123456fb",
        "WorkloadConfiguration": {
            "WorkloadName": "MYSQL",
            "Tier": "MYSQL",
            "Configuration": "{\"logs\":[{\"logGroupName\":\"MYSQL\",\"logPath\":\"/var/log/**\",\"logType\":\"MYSQL\",\"monitor\":true,\"encoding\":\"utf-8\"}]}"
        }
    }