**To describe a workload in an application**

This example uses the ``describe-workload`` command to describe a workload and its configuration from an application. ::

    aws application-insights describe-workload \
        --resource-group-name MYEC2 \
        --component-name arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56 \
        --workload-id w-2aaaf123-abc4-5678-a12e-d01234e56d7e

Output::

    {
        "WorkloadId": "w-2aaaf123-abc4-5678-a12e-d01234e56d7e",
        "WorkloadConfiguration": {
            "WorkloadName": "MYSQL",
            "Tier": "MYSQL",
            "Configuration": "{\"logs\":[],\"windowsEvents\":[{\"logGroupName\":\"WINDOWS_EVENTS-Application-MYEC2\",\"eventName\":\"Application\",\"eventLevels\":[\"WARNING\",\"ERROR\",\"CRITICAL\"],\"monitor\":true},{\"logGroupName\":\"WINDOWS_EVENTS-System-MYEC2\",\"eventName\":\"System\",\"eventLevels\":[\"WARNING\",\"ERROR\",\"CRITICAL\"],\"monitor\":true},{\"logGroupName\":\"WINDOWS_EVENTS-Security-MYEC2\",\"eventName\":\"Security\",\"eventLevels\":[\"WARNING\",\"ERROR\",\"CRITICAL\"],\"monitor\":true}]}"
        }
    }