**To list the workloads on a component**

This example uses the ``list-workloads`` command to lists the workloads that are configured on a specific component. ::

    aws application-insights list-workloads \
        --resource-group-name MYEC2 —component-name mycustomcomp

Output::

    {
        "WorkloadList": [{
            "WorkloadId": "w-1234a76f-a1b6-4e12-a2b1-a123d45678ed",
            "ComponentName": "mycustomcomp",
            "WorkloadName": "MYSQL",
            "Tier": "MYSQL"
        }]
    }